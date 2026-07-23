import os
import json
import pickle
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec
import time
from tiktoken import get_encoding
from langchain_openai import OpenAIEmbeddings
from deep_translator import GoogleTranslator
from openai import OpenAI
from fuzzywuzzy import fuzz

def update_pinecone_embeddings(file_path=None, index_name=None):

    # Load the API keys from environment variables first
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")

    if not OPENAI_API_KEY or not PINECONE_API_KEY:
        def load_env_variables():
            """Load API keys directly from .env file by parsing it manually."""
            # Check parent directory and current directory for .env
            env_paths = [
                os.path.join(os.path.dirname(__file__), '.env'),
                os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'),
                ".env"
            ]
            for path in env_paths:
                if os.path.exists(path):
                    api_keys = {}
                    try:
                        with open(path, 'r', encoding='utf-8') as file:
                            for line in file:
                                line = line.strip()
                                if not line or line.startswith('#'):
                                    continue
                                if '=' in line:
                                    key, value = line.split('=', 1)
                                    api_keys[key.strip()] = value.strip()
                        return api_keys
                    except Exception as e:
                        print(f"Error reading .env file at {path}: {e}")
            return {}

        api_keys = load_env_variables()
        OPENAI_API_KEY = OPENAI_API_KEY or api_keys.get("OPENAI_API_KEY")
        PINECONE_API_KEY = PINECONE_API_KEY or api_keys.get("PINECONE_API_KEY")

    if not OPENAI_API_KEY or not PINECONE_API_KEY:
        raise ValueError("API keys not found in environment variables or .env file")

    print("API keys loaded successfully")

    openai = OpenAI(api_key=OPENAI_API_KEY)
    pc = Pinecone(api_key=PINECONE_API_KEY)

    # Use provided file path or default
    if not file_path:
        file_path = "reports/new_scholarships_db.xlsx"
    
    df = pd.read_excel(file_path, engine="openpyxl")
    df = df.fillna("").astype(str)
    print(f"Dataset loaded successfully from {file_path} with {len(df)} rows")

    # Use provided index_name, or get from SiteConfig, or use default
    if not index_name:
        index_name = "scholarships-index-latest"
        try:
            from django.conf import settings
            from app.models import SiteConfig
            site_config = SiteConfig.objects.first()
            if site_config and site_config.active_dataset_index_name:
                index_name = site_config.active_dataset_index_name
                print(f"✓ Using custom index name from SiteConfig: {index_name}")
            else:
                print(f"✓ Using default index name: {index_name}")
        except Exception as e:
            print(f"Note: Could not load index name from SiteConfig, using default. Error: {e}")
    else:
        print(f"✓ Using provided index name: {index_name}")
    
    # Sanitize index name for Pinecone (underscores/spaces → hyphens, lowercase, alphanumeric only)
    # Pinecone requires: lowercase alphanumeric characters or '-' only
    import re
    index_name = index_name.strip().replace('_', '-').replace(' ', '-').lower()
    index_name = re.sub(r'[^a-z0-9-]', '', index_name)
    print(f"✓ Sanitized index name for Pinecone: {index_name}")
    
    embedding_dim = 1536  # text-embedding-3-small


    existing_indexes = [i.name for i in pc.list_indexes()]
    if index_name not in existing_indexes:
        print(f"Creating index: {index_name}")
        pc.create_index(
            name=index_name,
            dimension=embedding_dim,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
        print(f" Waiting for '{index_name}' to become active...")
        while True:
            desc = pc.describe_index(index_name)
            is_ready = desc.status.get("ready") if isinstance(desc.status, dict) else getattr(desc.status, "ready", False)
            if is_ready:
                print(f"Index '{index_name}' is now ready.")
                break
            time.sleep(3)
    else:
        print(f"Index '{index_name}' already exists.")

    index = pc.Index(index_name)


    enc = get_encoding("cl100k_base")

    def safe_truncate(text, max_tokens=8192):
        """Truncate text if it exceeds the model token limit."""
        tokens = enc.encode(text)
        if len(tokens) > max_tokens:
            print(f" Row truncated ({len(tokens)} → {max_tokens} tokens)")
            tokens = tokens[:max_tokens]
            text = enc.decode(tokens)
        return text


    def get_openai_embedding(text: str):
        """Generate embeddings using OpenAI API."""
        text = text.strip()
        if not text:
            return None

        text = safe_truncate(text)
        response = openai.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding


    # Determine the purpose column name in advance
    purpose_cols = ["Ändamål", "ändamål", "purpose", "Purpose", "Ändamål (Purpose)", "Ändamål/Purpose"]
    purpose_col = None
    for col in purpose_cols:
        if col in df.columns:
            purpose_col = col
            break
    
    if not purpose_col:
        # Fall back to checking any column containing 'purpose' or 'ändamål'
        for col in df.columns:
            if 'ändamål' in col.lower() or 'purpose' in col.lower():
                purpose_col = col
                break
    
    if not purpose_col:
        # If still not found, try the first column
        if len(df.columns) > 0:
            purpose_col = df.columns[0]
        else:
            raise ValueError("The Excel file has no columns.")
            
    print(f"Using column '{purpose_col}' for scholarship purpose text")

    def embed_and_upload(dataframe, start_idx=0, batch_size=100):
        """Generate embeddings and upload to Pinecone index in batches."""
        total_rows = len(dataframe)
        print(f"\nGenerating embeddings & uploading to '{index_name}' in batches of {batch_size}...")
        print(f"   Starting from row {start_idx} (Total rows in chunk: {total_rows})...")
        uploaded_count = 0

        rows = [row for _, row in dataframe.iterrows()]

        for batch_start in range(0, total_rows, batch_size):
            batch_rows = rows[batch_start:batch_start + batch_size]
            
            vectors_to_upsert = []
            texts_to_embed = []
            valid_indices = []
            
            for idx, row in enumerate(batch_rows):
                text = str(row.get(purpose_col, "")).strip()
                if text:
                    text = safe_truncate(text)
                    texts_to_embed.append(text)
                    valid_indices.append(idx)
            
            if not texts_to_embed:
                continue
                
            try:
                response = openai.embeddings.create(
                    model="text-embedding-3-small",
                    input=texts_to_embed
                )
                embeddings = [item.embedding for item in response.data]
            except Exception as e:
                print(f"Error calling OpenAI embedding API for batch {batch_start}: {e}")
                embeddings = []
                for text in texts_to_embed:
                    try:
                        emb = get_openai_embedding(text)
                        embeddings.append(emb)
                    except Exception as row_err:
                        print(f"Row embedding error: {row_err}")
                        embeddings.append(None)

            def clean_metadata(row_dict):
                cleaned = {}
                for key, val in row_dict.items():
                    if val is None:
                        continue
                    k_str = str(key).strip()
                    if not k_str:
                        continue
                    if isinstance(val, float) and (np.isnan(val) or np.isinf(val)):
                        continue
                    v_str = str(val).strip()
                    if v_str.lower() in ('nan', 'none', 'null'):
                        continue
                    if len(v_str) > 1000:
                        v_str = v_str[:1000]
                    cleaned[k_str] = v_str
                return cleaned

            for idx_in_batch, emb in enumerate(embeddings):
                if emb is None:
                    continue
                row_idx = valid_indices[idx_in_batch]
                row = batch_rows[row_idx]
                doc_id = str(start_idx + batch_start + row_idx)
                metadata = clean_metadata(row.to_dict())
                vectors_to_upsert.append({
                    "id": doc_id,
                    "values": emb,
                    "metadata": metadata
                })

            if vectors_to_upsert:
                index.upsert(vectors=vectors_to_upsert)
                uploaded_count += len(vectors_to_upsert)
                print(f"   ✓ Uploaded batch: {uploaded_count}/{total_rows} rows...")

        print(f"  Batch completed: {uploaded_count} rows uploaded.")



    chunk1 = df.iloc[:3200]
    chunk2 = df.iloc[3200:6400]


    if len(df) >= 10000:
        chunk3 = df.iloc[6400:]
        print(f"\n Dataset has {len(df)} rows - Processing 3 chunks")
        print(f"   Chunk 1: 0-{len(chunk1)-1} ({len(chunk1)} rows)")
        print(f"   Chunk 2: {len(chunk1)}-{len(chunk1)+len(chunk2)-1} ({len(chunk2)} rows)")
        print(f"   Chunk 3: {len(chunk1)+len(chunk2)}-{len(df)-1} ({len(chunk3)} rows)")
    else:
        chunk3 = None
        print(f"\nDataset has {len(df)} rows - Processing 2 chunks")
        print(f"   Chunk 1: 0-{len(chunk1)-1} ({len(chunk1)} rows)")
        print(f"   Chunk 2: {len(chunk1)}-{len(df)-1} ({len(chunk2)} rows)")

    print("\nUploading first batch (Chunk 1)...")
    uploaded_total = embed_and_upload(chunk1, start_idx=0)

    print("\nUploading second batch (Chunk 2)...")
    uploaded_total += embed_and_upload(chunk2, start_idx=3200)

    if chunk3 is not None:
        print("\nUploading third batch (Chunk 3)...")
        uploaded_total += embed_and_upload(chunk3, start_idx=6400)

    print("\nAll embeddings uploaded successfully!")
    print("=" * 60)

    # Update SiteConfig to mark upload as complete
    try:
        from app.models import SiteConfig
        site_config = SiteConfig.objects.first()
        if site_config:
            SiteConfig.objects.filter(id=site_config.id).update(
                pinecone_updated=True,
                upload_in_progress=False
            )
            print(f"\n✅ SUCCESS: Dataset uploaded to Pinecone index '{index_name}'")
            print(f"   Pinecone updated flag set to TRUE")
            print(f"   You can now query this index for scholarships")
    except Exception as e:
        print(f"⚠️  Warning: Could not update SiteConfig status: {e}")

    return {
        "total_rows": len(df),
        "rows_uploaded": uploaded_total,
    }





