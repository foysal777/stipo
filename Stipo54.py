import json
import re
from typing import List, Dict, Any, Tuple

from pinecone import Pinecone
from openai import OpenAI
from tiktoken import get_encoding
from deep_translator import GoogleTranslator
from fuzzywuzzy import fuzz
from dotenv import load_dotenv
import os

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

if not OPENAI_API_KEY or not PINECONE_API_KEY:
    raise ValueError("OPENAI_API_KEY or PINECONE_API_KEY not found in environment. Check your .env file.")


openai_client = OpenAI(api_key=OPENAI_API_KEY)
pc = Pinecone(api_key=PINECONE_API_KEY)

INDEX_NAME = "scholarships-index-latest"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536
DEFAULT_TOP_K = 200
MAX_CANDIDATES_FOR_LLM = 200
MIN_RESULTS = 10

enc = get_encoding("cl100k_base")
index = pc.Index(INDEX_NAME)
FIELD_MAP_SV = {
    "Name": "Namn",
    "Purpose": "Ändamål",
    "Study Level": "Utbildningsnivå",
    "Municipality": "Kommun",
    "Category": "Kategori",
    "Email": "Epost",
    "Website": "Websida",
    "Phone": "Telefon",
    "Assets": "Tillgångar",
    "Main Address": "Huvudadress",
    "Postal Code": "Postnr",
    "City": "Stad",
    "County": "Län",
    "Sport": "Sport",
}


NAME_INSTITUTION_TERMS = [
    "professur", "gästprofessur", "professuren",
    "lektorat", "docentur", "docenttjänst",
]


DIRECT_STUDENT_BENEFIT_OVERRIDES = [
    "stipendium till studerande", "stipendier till studerande",
    "stipendium till studenter", "stipendier till studenter",
    "bidrag till studerande", "bidrag till studenter",
    "till förmån för studerande", "till förmån för studenter",
    "studiestipendium", "studiestipendier",
    "studentstipendium", "studentstipendier",
]

BUSINESS_TERMS = [
    "business", "economics", "finance", "financial", "accounting", "banking",
    "management", "commerce", "entrepreneurship", "företagsekonomi", "ekonomi",
    "finans", "redovisning", "handel", "business administration", "marknadsföring",
    "marketing", "handelshögskolan", "ekonomisk", "ekonomiska",
    "nationalekonomi", "affärsinriktade studier", "affärsinriktad",
]

LAW_TERMS = [
    "law", "legal", "juridik", "juridisk", "affärsjuridik", "business law",
    "commercial law", "jurisprudence", "rättsvetenskap", "jurist", "juridiska",
    "folkrätt", "eg-rätt", "sjörätt", "transporträtt",
    "företagsjuridik", "företagsjuridiska",
    "rättsvetenskaplig", "rättsvetenskapliga",
    "affärsjuridiska",
    "sjörättens", "sjö- och transport",
    "transporträttens",
    "straffrätt", "civilrätt", "processrätt",
    "förvaltningsrätt", "miljörätt", "immaterialrätt",
    "arbetsrätt", "skatterätt", "familjerätt",
    "avtalsrätt", "offentlig rätt", "internationell rätt",
    "rättsinformation", "rättskällor",
    "juridikstuderande", "juriststuderande",
    "juridikstudent", "juriststudent",
    "juridiska fakultet", "juridiska fakulteten",
    "juridisk utbildning", "juristutbildning",
    "law student", "law faculty",
    # Commercial / trade law terms (Alexander feedback — handelsrätt case)
    "handelsrätt", "handelsrättens", "handelsrättslig",
    "köprätt", "kontraktsrätt",
    "bolags rätt", "bolagsrätt", "associationsrätt",
]

TECHNOLOGY_TERMS = [
    "technology", "teknik", "engineering", "ingenjör", "computer science",
    "datavetenskap", "it", "software", "programming", "programmering",
    "data science", "ai", "artificial intelligence", "machine learning",
    "cybersecurity", "nätverk", "elektronik", "elektroteknik",
    "civilingenjör", "teknisk", "tekniska",
]

NON_LAW_DOMAIN_TERMS = [
    "medicin", "medicine", "medical", "läkemedel", "pharmaceutical", "farmaci",
    "pharmacy", "hälsa", "health", "sjukvård", "healthcare", "nursing",
    "omvårdnad", "tandvård", "dentistry", "dental", "kirurgi", "surgery",
    "klinisk", "clinical", "biomedicin", "biomedical", "veterinär", "veterinary",
    "musik", "music", "musical", "konstnärlig", "artistic", "konst", "art",
    "teater", "theatre", "theater", "dans", "dance", "opera", "orkester",
    "biologi", "biology", "kemi", "chemistry", "fysik", "physics",
    "geologi", "geology", "astronomi", "astronomy", "botanik", "botany",
    "zoologi", "zoology", "ekologi", "ecology",
    "jordbruk", "agriculture", "lantbruk", "farming", "skogsbruk", "forestry",
    "karolinska", "karolinska institutet", "karolinska institutets",
    "medicinsk", "medicinska", "medicinare", "medicinstuderande",
    "sjöbefäl", "sjöfart", "sjöfartsutbildning", "nautisk", "nautiska",
    "sjöbefälsskola", "sjöbefälsskolans",
    "naturvetenskap", "naturvetenskaplig", "naturvetenskapliga",
    "matematik", "mathematics", "matematisk",
    "ingenjörsvetenskap", "teknikvetenskap",
    "naturbruk", "naturbruksgymnasiet",
    "drivhuset", "inkubator", "incubator",
]

NON_BUSINESS_DOMAIN_TERMS = [
    "medicin", "medicine", "medical", "läkemedel", "pharmaceutical",
    "sjukvård", "healthcare", "nursing", "tandvård", "dentistry",
    "kirurgi", "surgery", "klinisk", "clinical", "biomedicin",
    "musik", "music", "musical", "konstnärlig", "artistic",
    "teater", "theatre", "dans", "dance", "opera",
    "biologi", "biology", "kemi", "chemistry", "fysik", "physics",
    "jordbruk", "agriculture", "lantbruk", "skogsbruk", "forestry",
    "civilingenjör", "civilingenjörs",
    "master of science in engineering",
    "maskinteknik", "mechanical engineering",
    "datateknik", "computer engineering",
    "rymdteknik", "space technology",
    "energiteknik", "energy technology",
    "elektroteknik", "electrical engineering",
    "teknisk fysik", "engineering physics",
    "teknisk design", "technical design",
    "systemteknik", "systems engineering",
    "produktionsteknik", "production engineering",
    "materialteknik", "materials engineering",
    "byggteknik", "construction engineering",
    "fordonselektronik", "vehicle electronics",
    "programvaruteknik", "software engineering",
]

NON_TECH_DOMAIN_TERMS = [
    "medicin", "medicine", "musik", "music", "konstnärlig", "artistic",
    "jordbruk", "agriculture", "lantbruk", "teater", "theatre",
    "dans", "dance", "opera", "juridik", "law", "legal",
]


STRICT_RESEARCH_ONLY_TERMS = [
    "doktorand", "doktorandnivå", "forskarutbildning", "forskarstuderande",
    "postdoktoral", "postdoc", "postdoctoral", "postdoktor", "gästprofessur",
    "efter avlagd doktorsexamen",
    "doctoral", "doctorate", "phd", "ph.d",
    "dissertation", "avhandling",
    "forskartjänst", "doktorsexamen", "licentiatexamen",
    "researcher position",
    "antagna till forskarutbildning",
    "studier efter avlagd doktorsexamen",
    "bedriver studier efter avlagd doktorsexamen",
]

ADVANCED_LEVEL_EXCLUSION_PHRASES = [
    "minst avancerad nivå",
    "avancerad nivå minst",
    "lägst avancerad nivå",
    "avancerad nivå eller högre",
]

DOCENT_EXCLUSIVE_TERMS = [
    "avlöning av en docent",
    "avlöning av docent",
    "till avlöning av en lärare (docent)",
    "docenttjänst",
    "docentur",
]

SOFT_RESEARCH_TERMS = [
    "research", "forskning", "research fund", "forskningsfond",
    "research foundation", "forskningsstiftelse", "scientific research",
    "vetenskaplig forskning", "vetenskapligt arbete",
    "vetenskapligt", "forskningsarbete"
]


INSTITUTION_SUPPORT_TERMS = [
    "guest professorship", "professorship", "professur", "professurer",
    "gästprofessur",
    "chair",
    "lektor", "lektorat",
    "avlöning av en lärare",
    "avlöning av en docent",
    "avlöning av docent",
    "avlöning av en professor",
]

INSTITUTION_COST_TERMS = [
    "seminariebibliotekets", "seminariebibliotek",
    "böcker till", "inköp av böcker",
    "bibliotekets",
    "institutionens drift",
    "underhåll av",
    "departmental costs",
    "faculty salary", "faculty salaries",
    "till en professur",
    "till professur",
    "medel skall användas till en professur",
    "till avlöning",
    "finansiera professuren",
    "helt eller delvis finansiera professuren",
    "inköp av böcker för seminariebiblioteket",
    "böcker för seminariebiblioteket",
    "inköp av böcker för seminarie",
]

ENTREPRENEURSHIP_SUPPORT_TERMS = [
    "drivhuset", "incubator", "inkubator", "startup support",
    "entrepreneurship support", "innovation hub", "innovation environment"
]

STRONG_DIRECT_SCHOLARSHIP_TERMS = [
    "stipendium", "stipend", "scholarship", "grant", "bidrag",
    "stipendiefond", "resestipendium", "studiestipendium",
    "stipendier", "studiebidrag"
]

BUSINESS_SCHOOL_STUDENT_TERMS = [
    "handelshögskolan", "school of business", "business school",
    "studentkår", "student union", "ekonomisk utbildning",
    "school of economics",
]

UNDERGRAD_TERMS = [
    "undergraduate", "bachelor", "bachelors", "candidate", "kandidat",
    "grundnivå", "grundutbildning", "kandidatexamen"
]



UNDERGRAD_INDICATOR_TERMS = [
    "grundutbildning", "grundnivå", "årskurs",
    "bachelor", "undergraduate",
    "kurser på grundnivå",
    "grundutbildningsnivå",
    "bachelor studies", "bachelor students",
]

DUAL_PURPOSE_PHRASES = [
    "forskning och utbildning",
    "utbildning och forskning",
    "undervisning och forskning",
    "forskning och undervisning",
    "vetenskaplig undervisning och forskning",
    "forskning, utbildning",
    "utbildning, forskning",
    "undervisning, forskning",
    "forskning och utbildning inom",
    "stödja forskning och utbildning",
    "främja forskning och utbildning",
    "forskning och undervisning vid",
    "stödja forskning och undervisning",
    "forskning och vetenskaplig undervisning",
    "vetenskaplig forskning och undervisning",
    "vetenskaplig forskning och vetenskaplig undervisning",
    "forskning och vetenskaplig undervisning- eller studieverksamhet",
    "undervisning- eller studieverksamhet",
    "forskning eller undervisning",
    "forskning eller utbildning",
    "utbildning eller forskning",
    "forskning, undervisning",
    "forskning samt utbildning",
    "forskning samt undervisning",
    "utbildning samt forskning",
    "forskning och utvecklingsverksamhet",
    "forskning och studieverksamhet",
    "forskning och vetenskaplig studieverksamhet",
    "vetenskaplig forskning och studieverksamhet",
    "främja forskning och undervisning",
    "stödja forskning och studieverksamhet",
    "främja och stödja forskning",
    "främja och stödja utbildning",
]

THESIS_STUDENT_TERMS = [
    "examensarbete", "examensarbeten",
    "kandidatuppsats", "kandidatuppsatser",
    "masteruppsats", "masteruppsatser",
    "magisteruppsats", "magisteruppsatser",
    "uppsats", "uppsatser",
    "slutarbete",
    "degree project",
    "bachelor thesis", "bachelor's thesis",
    "master thesis", "master's thesis",
    "uppsatstävling",
    "tävla med kandidat", "tävla med magister", "tävla med master",
]

FACULTY_WIDE_TERMS = [
    "studerande vid", "studenter vid", "elever vid",
    "studerande vid juridiska", "studenter vid juridiska",
    "studerande vid handelshögskolan", "studenter vid handelshögskolan",
    "studerande vid tekniska", "studenter vid tekniska",
    "studerande vid chalmers", "studenter vid chalmers",
    "studerande vid kth", "studenter vid kth",
    "studerande vid universitetet", "studenter vid universitetet",
    "studerande vid högskolan", "studenter vid högskolan",
    "inskrivna studerande", "inskrivna studenter",
    "studerande i ekonomi", "studerande i juridik",
    "studerande i teknik",
    "elever vid chalmers", "elever vid kth",
]

STRONG_STUDENT_TERMS = [
    "till studerande", "åt studerande", "för studerande",
    "till studenter", "åt studenter", "för studenter",
    "till elever", "åt elever", "för elever",
    "till student", "för student",
    "studerande vid", "studenter vid", "elever vid",
    "studerande som", "studenter som",
    "inskrivna studerande", "inskrivna studenter",
    "studiestipendium", "studiestipendier",
    "studentstipendium", "studentstipendier",
    "gymnasieelever",
    "for students", "to students",
    "bachelor students", "bachelor studies",
    "undergraduate students",
    "uppmuntra studenter", "stödja studenter",
    "stipendier till studenter", "stipendier till studerande",
    "stipendium till studenter",
    "kandidat", "kandidatuppsats", "kandidatuppsatser",
    "kandidatexamen", "kandidat-", "kandidatnivå",
    "bachelorstudent", "bachelorstudenter", "bachelor student",
    "grundnivå", "grundutbildning",
    "kurser på grundnivå",
    "årskurs 1", "årskurs 2", "årskurs 3", "årskurs",
    "masteruppsats", "masteruppsatser", "masterexamen",
    "magisteruppsats", "masternivå",
    "master's theses", "master's thesis",
    "bachelor's theses", "bachelor's thesis",
    "examensarbete", "examensarbeten",
    "uppsats", "uppsatser", "slutarbete",
    "juridiska fakulteten", "juridisk fakultet",
    "juridikstuderande", "juriststuderande",
    "studerande vid juridiska", "studenter vid juridiska",
    "handelshögskolan",
    "studerande vid handelshögskolan",
    "studenter vid handelshögskolan",
    "ekonomistuderande",
    "teknologer", "teknologer vid",
    "civilingenjörsstudenter", "ingenjörsstudenter",
    "studerande vid tekniska",
    "studenter vid chalmers", "studenter vid kth",
    "vid sidan av studier", "vid sidan av studierna",
    "driver du eget företag vid sidan av studier",
    "affärsinriktade studier", "ledarskap i affärs", "affärsinriktad",
    "utbytesstudier", "utbyte", "fältstudier",
    "studieresa", "studieresor",
    "vidarestudier", "fortsatta studier",
    "högskolestudier", "universitetsstudier",
    "uppsatstävling",
    "tävla med kandidat", "tävla med magister", "tävla med master",
    "studenttävling",
    "studerande", "studenter", "student",
    "lärjungar", "lärjunge", "elever",
]

WEAK_STUDENT_TERMS = [
    "studier", "utbildning", "studies",
    "education", "undervisning",
]

RESEARCH_BENEFICIARY_TERMS = [
    "till forskare", "åt forskare", "för forskare",
    "forskartjänst", "forskarstipendium", "forskarstipendier",
    "forskningsbidrag", "forskningsanslag",
    "forskarstuderande",
    "forskare vid", "forskare och",
    "for researchers", "research grant", "research scholarship",
    "researcher exchange", "sabbatical",
    "preferably a doctorate", "helst doktorsexamen",
    "individual researchers", "individuella forskare",
    "antagna till forskarutbildning",
    "studier efter avlagd doktorsexamen",
    "bedriver studier efter avlagd doktorsexamen",
]

RESEARCH_PRIMARY_PHRASES = [
    "främja vetenskaplig forskning",
    "främja forskning",
    "stödja forskning",
    "promote scientific research",
    "promote research",
    "support scientific research",
    "support research",
    "primarily to support scientific research",
    "huvudsakliga ändamål att främja forskning",
]

RESEARCH_STUDY_LEVELS = [
    "research", "doctoral", "forskning", "doktorsexamen",
    "forskarutbildning", "postdoc",
]

SWEDISH_PLACE_NAMES = {
    "trollhättan", "gävle", "lund", "malmö", "göteborg", "stockholm",
    "uppsala", "linköping", "örebro", "umeå", "jönköping", "norrköping",
    "helsingborg", "västerås", "borås", "sundsvall", "östersund",
    "karlstad", "växjö", "kalmar", "kristianstad", "halmstad",
    "luleå", "kiruna", "skellefteå", "falun", "borlänge",
    "visby", "hudiksvall", "härnösand", "nyköping", "eskilstuna",
    "norrtälje", "enköping", "tierp", "mora", "ludvika",
    "örnsköldsvik", "sollefteå", "kramfors", "ånge",
}

MEDICAL_EXPLICIT_TERMS = [
    "medicine studerande", "medicinstuderande", "medicinare",
    "medicine studerandes", "medicinska fakulteten",
    "karolinska institutet", "karolinska institutets", "karolinska",
    "medicinska högskolan",
    "läkarexamen", "läkarutbildning",
    "tandläkar", "tandläkarinstitutet", "tandläkarutbildning",
    "medicinsk forskning", "medicinsk vetenskaplig forskning",
    "medicinska området", "det medicinska området",
    "medicinsk", "medicinska", "medicinskt",
    "njurmedicinsk", "njurmedicin",
    "kirurgiska kliniken", "kirurgiska",
    "gynekologisk", "onkologi", "gynekologisk onkologi",
    "sjukvårdsverksamhet", "kvalificerad sjukvårdsverksamhet",
    "sjukvård", "kliniskt betydelsefull",
    "klinisk", "kliniskt", "kliniska",
    "sjöbefäl", "sjöbefälsskola", "sjöbefälsskolans",
    "naturvetenskapliga", "naturvetenskaplig",
    "tekniska gymnasiestudier",
]

MEDICAL_TERMS = [
    "medicine", "medical", "medicin", "medicinsk", "medicinska", "medicinskt",
    "medicinare", "medicinstuderande", "medicine studerande",
    "läkare", "läkarexamen", "läkarutbildning", "läkarprogrammet",
    "sjukvård", "healthcare", "health", "hälsa", "hälsovetenskap",
    "nursing", "omvårdnad", "sjuksköterska", "sjuksköterskeprogrammet",
    "tandvård", "dentistry", "dental", "tandläkare", "tandläkarutbildning",
    "farmaci", "pharmacy", "pharmaceutical", "läkemedel", "apotekare",
    "biomedicin", "biomedical", "biomedicinsk",
    "kirurgi", "surgery", "surgical", "kirurgisk",
    "klinisk", "kliniskt", "kliniska", "clinical",
    "patologi", "pathology", "onkologi", "oncology",
    "gynekologi", "gynekologisk", "pediatrik", "pediatrics",
    "psykiatri", "psychiatry", "neurologi", "neurology",
    "fysiologi", "physiology", "anatomi", "anatomy",
    "epidemiologi", "epidemiology",
    "folkhälsa", "public health",
    "veterinär", "veterinary",
    "karolinska", "karolinska institutet",
    "medicinsk forskning", "medical research",
    "sjukhus", "hospital",
    "rehabilitering", "rehabilitation",
    "geriatrik", "geriatrics",
    "reumatologi", "rheumatology",
    "njurmedicin", "njurmedicinsk",
    "kardiologi", "cardiology",
    "dermatologi", "dermatology",
]

NON_MEDICAL_DOMAIN_TERMS = [
    "juridik", "juridisk", "juridiska", "affärsjuridik", "rättsvetenskap",
    "law", "legal",
    "företagsekonomi", "handelshögskolan", "business administration",
    "maskinteknik", "mechanical engineering",
    "datateknik", "computer engineering", "programvaruteknik",
    "elektroteknik", "electrical engineering",
    "civilingenjör", "civilingenjörs",
    "byggteknik", "construction engineering",
    "arkitektur", "architecture",
    "musik", "music", "konstnärlig", "artistic",
    "teater", "theatre", "dans", "dance", "opera",
    "jordbruk", "agriculture", "lantbruk", "skogsbruk", "forestry",
    "sjöbefäl", "sjöfart", "nautisk",
]

INDIVIDUAL_ACCESSIBLE_MARKERS = [
    "stipendium", "stipendier", "stipendiat",
    "resestipendium", "resestipendier",
    "forskarstipendie", "forskarstipendium",
    "studiestipendium", "studiestipendier",
    "bidrag till enskilda",
    "bidrag till fysiska personer",
    "bidrag till person",
    "ekonomiskt stöd till",
    "ekonomiskt bidrag till",
    "anslag till enskilda",
    "anslag till fysiska",
    "åt studerande", "åt studenter",
    "åt forskare", "åt doktorand",
    "till studerande", "till studenter",
    "till forskare", "till doktorand",
    "till person", "till personer",
    "till enskild", "till enskilda",
    "ansökan", "ansöka", "sökande",
    "den sökande", "sökanden",
    "meriterade sökande",
    "välmeriterade sökande",
    "resor", "studieresa", "studieresor",
    "utlandsstudier", "utlandsvistelse",
    "utbyte", "utbytesstudier",
]

INSTITUTIONAL_ONLY_MARKERS = [
    "endast till institution",
    "enbart till institution",
    "anslag till universitetet",
    "anslag till högskolan",
    "anslag till fakulteten",
    "bidrag till institutionen",
    "bidrag till universitetet",
    "bidrag till högskolan",
    "lönekostnader", "lönekostnad",
    "avlöning av", "avlöna",
    "personalkostnader", "personalkostnad",
    "driftskostnader", "driftskostnad",
    "lokalkostnader", "lokalkostnad",
    "utrustning till institutionen",
    "inköp av utrustning",
    "laboratorieutrustning",
    "byggnation av",
    "renovering av",
    "finansiera professur",
    "inrätta professur",
    "upprätthålla professur",
    "gästprofessors verksamhet",
    "bibliotekets verksamhet",
    "inköp av böcker till",
    "samlingens underhåll",
    "ej till enskilda",
    "inte till enskilda",
    "ej personliga",
    "inte personliga stipendier",
]


STRONG_TECH_SINGLE_MATCH_TERMS = [
    "civilingenjör",
    "tekniska högskolan",
    "tekniska hogskolan",
    "teknisk forskning",
    "teknisk utbildning",
    "teknologer vid chalmers",
    "chalmers tekniska",
    "elmaskinteknik",
    "kraftelektronik",
    "produktionsteknik",
    "miljöteknik",
    "elektroteknik",
    "maskinteknik",
    "byggteknik",
    "programvaruteknik",
    "datateknik",
    "mekatronik",
    "fordonsteknik",
    "flygteknik",
    "rymdteknik",
    "energiteknik",
    "materialteknik",
    "bioteknik",
    "kemiteknik",
    "industriell ekonomi",
    "kemins och elektronikens",
    "kemins område",
    "elektronikens område",
    "skoglig och skogsindustriell",
    "skogsindustriell verksamhet",
    "skoglig verksamhet",
]


FORESTRY_NATURAL_RESOURCE_TERMS = [
    "skoglig", "skogsindustriell", "skogsindustri", "skogsbruk",
    "skogsvetenskap", "skogsforskning", "skogsnäring",
    "gruv", "gruvnäring", "mineral", "mineralnäring",
    "bergsbruk", "bergsindustri",
]



def normalize_text(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", str(text).strip().lower())


def contains_any(text: str, terms: List[str]) -> bool:
    t = normalize_text(text)
    return any(term in t for term in terms)


def contains_any_stem(text: str, terms: List[str], min_stem_len: int = 6) -> bool:
    t = normalize_text(text)
    for term in terms:
        if term in t:
            return True
        if len(term) >= min_stem_len:
            stem = term[:min_stem_len]
            if stem in t:
                return True
    return False


def match_tech_terms_word_boundary(text: str, terms: List[str]) -> List[str]:
    
    t = normalize_text(text)
    matched = []
    for term in terms:
        if ' ' in term:
            # Multi-word root: exact substring is safe (phrase is specific)
            if term in t:
                matched.append(term)
        else:
            pattern = re.compile(r'\b' + re.escape(term) + r'\w*', re.IGNORECASE)
            if pattern.search(t):
                matched.append(term)
    return matched


def count_matches(text: str, terms: List[str]) -> int:
    t = normalize_text(text)
    return sum(1 for term in terms if term in t)


def get_matched_terms(text: str, terms: List[str]) -> List[str]:
    """Returns the actual terms that matched. Used for debug traceability."""
    t = normalize_text(text)
    return [term for term in terms if term in t]


def combined_scholarship_text(sch: Dict[str, Any]) -> str:
    return normalize_text(" ".join([
        str(sch.get("Name", "")),
        str(sch.get("Purpose", "")),
        str(sch.get("Category", "")),
        str(sch.get("Study Level", ""))
    ]))


def scholarship_purpose_text(sch: Dict[str, Any]) -> str:
    return normalize_text(str(sch.get("Purpose", "")))


def _exclusion_purpose_text(sch: Dict[str, Any]) -> str:
    """
    Text used for EXCLUSION decisions — Name + Purpose ONLY.
    Do NOT include Study Level or Category.
    """
    return normalize_text(" ".join([
        str(sch.get("Name", "")),
        str(sch.get("Purpose", "")),
    ]))


def expand_user_query_for_embedding(user_purpose: str) -> str:
    text = normalize_text(user_purpose)
    expansions = []
    if any(k in text for k in ["finance", "finans", "economics", "ekonomi"]):
        expansions.extend(["business", "accounting", "management", "commerce",
                           "företagsekonomi", "handelshögskolan"])
    if any(k in text for k in ["law", "juridik", "legal", "rättsvetenskap"]):
        expansions.extend([
            "juridik", "juridiska studier", "rättsvetenskap", "jurist",
            "folkrätt", "affärsjuridik", "eg-rätt", "företagsjuridik",
            "sjörätt", "transporträtt", "stipendium juridik"
        ])
    if any(k in text for k in ["technology", "teknik", "engineering", "computer", "software"]):
        expansions.extend(["teknik", "ingenjör", "datavetenskap", "it", "software",
                           "civilingenjör", "teknisk"])
    if any(k in text for k in ["medicine", "medical", "medicin", "healthcare",
                                "health", "nursing", "pharmacy", "dental",
                                "läkare", "sjukvård", "hälsa"]):
        expansions.extend([
            "medicin", "medicinsk", "läkarutbildning", "sjukvård",
            "karolinska", "biomedicin", "klinisk", "hälsovetenskap",
            "farmaci", "tandvård", "stipendium medicin"
        ])
    if expansions:
        return f"{user_purpose} related fields: {', '.join(sorted(set(expansions)))}"
    return user_purpose


def safe_translate(text: str, source: str, target: str) -> str:
    try:
        return GoogleTranslator(source=source, target=target).translate(text)
    except Exception:
        return text


def is_law_relevant(text: str) -> bool:
    return contains_any(text, LAW_TERMS)


def is_user_seeking_law(user_purpose: str) -> bool:
    return contains_any(user_purpose, LAW_TERMS)


def get_user_domain(user_purpose: str) -> str:
    text = normalize_text(user_purpose)
    if is_user_seeking_law(text):
        return "law"
    if contains_any(text, BUSINESS_TERMS):
        return "business"
    if contains_any(text, TECHNOLOGY_TERMS):
        return "technology"
    if contains_any(text, MEDICAL_TERMS):
        return "medical"
    return "general"


def is_domain_match(text: str, user_purpose: str) -> bool:
    domain = get_user_domain(user_purpose)
    if domain == "law":
        return is_law_relevant(text)
    elif domain == "business":
        return contains_any(text, BUSINESS_TERMS)
    elif domain == "technology":
        return contains_any(text, TECHNOLOGY_TERMS)
    elif domain == "medical":
        return contains_any(text, MEDICAL_TERMS)
    return False


RESEARCH_USER_TERMS = [
    "research", "forskning", "doctoral", "doktorand", "phd", "ph.d",
    "postdoc", "postdoctoral", "forskarutbildning", "researcher",
    "forskare", "dissertation", "avhandling",
]


def is_research_user(user_purpose: str) -> bool:
    return contains_any(normalize_text(user_purpose), RESEARCH_USER_TERMS)


def is_strongly_student_facing(text: str) -> bool:
    return contains_any(text, STRONG_STUDENT_TERMS)


def has_undergrad_indicators(text: str) -> bool:
    return contains_any(text, UNDERGRAD_INDICATOR_TERMS)


def is_research_beneficiary(text: str) -> bool:
    return contains_any(text, RESEARCH_BENEFICIARY_TERMS)


def is_research_primary(text: str) -> bool:
    return contains_any(text, RESEARCH_PRIMARY_PHRASES)


def has_research_study_level(sch: Dict) -> bool:
    level = normalize_text(str(sch.get("Study Level", "")))
    return contains_any(level, RESEARCH_STUDY_LEVELS)


def _has_research_and_education_coexistence(text: str) -> bool:
    has_research = contains_any(text, SOFT_RESEARCH_TERMS)
    education_terms = [
        "utbildning", "undervisning", "studieverksamhet",
        "education", "teaching", "lärande",
        "studiestöd",
    ]
    has_education = contains_any(text, education_terms)
    return has_research and has_education


def _has_individual_grant_language(text: str) -> bool:
    individual_grant_phrases = [
        "delar ut bidrag", "delar ut stipendium",
        "bidrag och stipendium", "stipendium och bidrag",
        "bidrag till fysiska", "stipendium till fysiska",
        "ekonomiska bidrag", "ekonomiskt bidrag",
        "bidrag till enskilda", "anslag till enskilda",
    ]
    return contains_any(text, individual_grant_phrases)


def is_genuinely_dual_purpose(text: str) -> bool:
    has_dual_phrase = contains_any(text, DUAL_PURPOSE_PHRASES)
    has_broad_coexistence = _has_research_and_education_coexistence(text)

    if not has_dual_phrase and not has_broad_coexistence:
        return False

    has_strict_doctoral = contains_any(text, STRICT_RESEARCH_ONLY_TERMS)
    has_student = is_strongly_student_facing(text)
    has_undergrad = has_undergrad_indicators(text)

    if has_strict_doctoral and not has_student and not has_undergrad:
        return False

    return True


def has_thesis_student_terms(text: str) -> bool:
    return contains_any(text, THESIS_STUDENT_TERMS)


def is_faculty_wide_scholarship(text: str) -> bool:
    return contains_any(text, FACULTY_WIDE_TERMS)


def classify_scholarship(sch: Dict) -> str:
    
    text = combined_scholarship_text(sch)
    purpose = scholarship_purpose_text(sch)
    content_text = _exclusion_purpose_text(sch)
    has_undergrad = has_undergrad_indicators(purpose) or has_undergrad_indicators(text)
    strong_student = is_strongly_student_facing(purpose) or is_strongly_student_facing(text)
    dual = is_genuinely_dual_purpose(purpose)
    has_thesis = has_thesis_student_terms(text)
    has_faculty = is_faculty_wide_scholarship(text)
    research_beneficiary = is_research_beneficiary(purpose)
    research_primary = is_research_primary(purpose)
    research_level = has_research_study_level(sch)
    has_strict_doctoral = contains_any(content_text, STRICT_RESEARCH_ONLY_TERMS)
    has_soft_research = contains_any(content_text, SOFT_RESEARCH_TERMS)
    has_weak_student = contains_any(purpose, WEAK_STUDENT_TERMS)

    if has_undergrad:
        return "student"
    if has_thesis:
        return "student"
    if has_faculty and not has_strict_doctoral:
        return "student"
    if strong_student and not has_strict_doctoral:
        return "student"
    if has_strict_doctoral and not strong_student and not has_undergrad:
        return "research"
    if strong_student and has_strict_doctoral:
        return "mixed"
    if dual:
        return "mixed"
    if research_beneficiary and research_level:
        return "research"
    if research_primary and not strong_student and not has_undergrad:
        return "research"
    if research_beneficiary and has_soft_research and not strong_student:
        return "research"
    if has_soft_research and research_level and not strong_student and not has_undergrad:
        return "research"
    if has_soft_research and not has_weak_student and not strong_student and not has_undergrad:
        return "research"
    if has_soft_research and has_weak_student and research_primary:
        return "research"
    if has_soft_research and has_weak_student:
        return "mixed"

    return "neutral"


def _has_undergraduate_safe_harbor(text: str, purpose: str) -> bool:
    """CENTRAL SAFE HARBOR CHECK - used by all exclusion functions."""
    if has_undergrad_indicators(text):
        return True
    if has_thesis_student_terms(text):
        return True
    if is_faculty_wide_scholarship(text):
        return True
    if is_genuinely_dual_purpose(text) or is_genuinely_dual_purpose(purpose):
        return True
    if is_strongly_student_facing(text):
        return True
    return False


def _is_exclusively_doctoral(sch: Dict) -> Tuple[bool, str]:
    full_text = combined_scholarship_text(sch)
    purpose = scholarship_purpose_text(sch)
    excl_text = _exclusion_purpose_text(sch)

    if _has_undergraduate_safe_harbor(full_text, purpose):
        return False, ""

    strict_matches = get_matched_terms(excl_text, STRICT_RESEARCH_ONLY_TERMS)
    if strict_matches:
        return True, f"exclusively doctoral/postdoc (matched in purpose: {strict_matches})"

    advanced_matches = get_matched_terms(excl_text, ADVANCED_LEVEL_EXCLUSION_PHRASES)
    if advanced_matches:
        return True, f"advanced level minimum requirement (matched in purpose: {advanced_matches})"

    docent_matches = get_matched_terms(excl_text, DOCENT_EXCLUSIVE_TERMS)
    if docent_matches:
        return True, f"exclusively for docent position (matched in purpose: {docent_matches})"

    return False, ""


def _is_institution_support(sch: Dict, user_purpose: str) -> Tuple[bool, str]:
  
    full_text = combined_scholarship_text(sch)
    purpose = scholarship_purpose_text(sch)
    excl_text = _exclusion_purpose_text(sch)
    name = normalize_text(str(sch.get("Name", "")))

    user_domain = get_user_domain(user_purpose)


    purpose_has_user_domain = False
    if user_domain == "law":
        purpose_has_user_domain = contains_any(purpose, LAW_TERMS)
    elif user_domain == "business":
        purpose_has_user_domain = contains_any(purpose, BUSINESS_TERMS)
    elif user_domain == "technology":
        purpose_has_user_domain = contains_any(purpose, TECHNOLOGY_TERMS)
    elif user_domain == "medical":
        purpose_has_user_domain = contains_any(purpose, MEDICAL_TERMS)

    if purpose_has_user_domain:

        hard_cost_markers = [
            "lönekostnader", "lönekostnad",
            "avlöning av en professor", "avlöning av en lärare",
            "finansiera professuren", "inrätta professur",
            "upprätthålla professur", "gästprofessors verksamhet",
            "inköp av böcker för seminariebiblioteket",
            "böcker för seminariebiblioteket",
        ]
        if not contains_any(excl_text, hard_cost_markers):
            return False, ""


    name_inst_matches = get_matched_terms(name, NAME_INSTITUTION_TERMS)
    if name_inst_matches:
        if contains_any(purpose, DIRECT_STUDENT_BENEFIT_OVERRIDES):
            return False, ""
        return True, f"name indicates institution support (matched in name: {name_inst_matches})"

    if _has_undergraduate_safe_harbor(full_text, purpose):
        return False, ""

    if any(word in normalize_text(user_purpose)
           for word in ["professor", "faculty", "fakultet"]):
        return False, ""

    inst_matches = get_matched_terms(excl_text, INSTITUTION_SUPPORT_TERMS)
    if inst_matches:
        return True, f"institution support - no student benefit (matched: {inst_matches})"

    cost_matches = get_matched_terms(excl_text, INSTITUTION_COST_TERMS)
    if cost_matches:
        return True, f"institutional costs - no student benefit (matched: {cost_matches})"

    docent_matches = get_matched_terms(excl_text, DOCENT_EXCLUSIVE_TERMS)
    if docent_matches:
        return True, f"docent salary/position - institution support (matched: {docent_matches})"

    return False, ""


def should_exclude_research_doctoral(sch: Dict, user_purpose: str) -> Tuple[bool, str]:
    full_text = combined_scholarship_text(sch)
    purpose = scholarship_purpose_text(sch)
    excl_text = _exclusion_purpose_text(sch)

    if is_research_user(user_purpose):
        return False, ""

    if _has_undergraduate_safe_harbor(full_text, purpose):
        return False, ""

    if is_domain_match(excl_text, user_purpose):
        return False, ""

    if _has_research_and_education_coexistence(excl_text):
        return False, ""

    if _has_individual_grant_language(excl_text):
        return False, ""

    if contains_any(excl_text, INDIVIDUAL_ACCESSIBLE_MARKERS):
        return False, ""

    is_doctoral, reason = _is_exclusively_doctoral(sch)
    if is_doctoral:
        return True, reason

    is_undergrad_user = contains_any(user_purpose, UNDERGRAD_TERMS)

    if is_undergrad_user and contains_any(excl_text, SOFT_RESEARCH_TERMS):
        inst_only_matches = get_matched_terms(excl_text, INSTITUTIONAL_ONLY_MARKERS)
        if inst_only_matches:
            return True, f"institutional-only research fund (matched: {inst_only_matches[:5]})"
        return False, ""

    return False, ""


def should_exclude_entity_type(sch: Dict, user_purpose: str) -> Tuple[bool, str]:
   
    full_text = combined_scholarship_text(sch)
    purpose = scholarship_purpose_text(sch)
    excl_text = _exclusion_purpose_text(sch)
    name = normalize_text(str(sch.get("Name", "")))
    user_domain = get_user_domain(user_purpose)

    if user_domain == "law" and is_law_relevant(excl_text):
        return False, ""
    if user_domain == "business" and contains_any(excl_text, BUSINESS_TERMS):
        return False, ""
    if user_domain == "technology" and contains_any(excl_text, TECHNOLOGY_TERMS):
        return False, ""
    if user_domain == "medical" and contains_any(excl_text, MEDICAL_TERMS):
        return False, ""


    if user_domain == "law":

        tech_cross_domain_safe = [
            "ekonomisk och teknisk", "teknisk och ekonomisk",
            "ekonomi och teknik", "teknik och ekonomi",
            "samhällsvetenskaplig och teknisk",
        ]
        if not contains_any(excl_text, tech_cross_domain_safe):

            strong_tech_matches = match_tech_terms_word_boundary(excl_text, STRONG_TECH_SINGLE_MATCH_TERMS)
            if strong_tech_matches:
                return True, f"strong tech/engineering domain for law user (matched: {strong_tech_matches[:3]})"

        # Tier 2 — general tech terms, require 2+ matches
        tech_general_matches = get_matched_terms(excl_text, TECHNOLOGY_TERMS)
        if len(tech_general_matches) >= 2:
            if not contains_any(excl_text, LAW_TERMS):
                return True, f"tech/engineering domain for law user ({len(tech_general_matches)} matches: {tech_general_matches[:3]})"

        # Medical explicit check
        medical_matches = get_matched_terms(excl_text, MEDICAL_EXPLICIT_TERMS)
        if medical_matches:
            if not contains_any(excl_text, LAW_TERMS):
                return True, f"explicit medical/non-law domain for law user (matched: {medical_matches[:5]})"

    if user_domain == "medical":
        law_explicit = [
            "juridik", "juridisk", "juridiska", "affärsjuridik",
            "rättsvetenskap", "jurist", "juridiska fakulteten",
            "sjörätt", "transporträtt",
        ]
        law_matches = get_matched_terms(excl_text, law_explicit)
        if law_matches:
            if not contains_any(excl_text, MEDICAL_TERMS):
                return True, f"explicit law domain for medical user (matched: {law_matches[:5]})"

    if user_domain == "business":
        medical_matches = get_matched_terms(excl_text, MEDICAL_EXPLICIT_TERMS)
        if medical_matches:
            if not contains_any(excl_text, BUSINESS_TERMS):
                return True, f"explicit medical domain for business user (matched: {medical_matches[:5]})"

    if user_domain == "technology":
        medical_matches = get_matched_terms(excl_text, MEDICAL_EXPLICIT_TERMS)
        if medical_matches:
            if not contains_any(excl_text, TECHNOLOGY_TERMS):
                return True, f"explicit medical domain for technology user (matched: {medical_matches[:5]})"

    is_inst, inst_reason = _is_institution_support(sch, user_purpose)
    if is_inst:
        return True, inst_reason

    below_university_only_terms = [
        "elev i grundskolan", "grundskolan",
        "grundskoleelev", "grundskoleelever",
        "naturbruksgymnasiet", "naturbruk",
        "gymnasieskolas samfond",
        "lärjunge", "lärjungar",
        "realskolan", "realskolans",
        "läroverket", "läroverk",
        "abiturient",
    ]

    name_school_patterns = [
        "skolfond", "skolas stipendiestiftelse", "skolas samfond",
        "skolans stipendie", "skolans fond",
    ]
    gymnasium_only_terms = [
        "gymnasieelever", "gymnasieelev", "gymnasieskolan", "gymnasiet",
    ]
    university_pathway_terms = [
        "högskola", "universitet", "universitetsstudier", "högskolestudier",
        "sökt utbildning på högskola", "sökt utbildning på universitet",
        "fortsätta studera", "vidarestudier vid",
        "högskoleutbildning", "universitetsutbildning",
    ]

    if "studentexamen" in excl_text:
        if not contains_any(excl_text, university_pathway_terms):
            return True, "below university level only (matched: ['studentexamen'] with no university pathway)"

    if contains_any(excl_text, below_university_only_terms):
        if not contains_any(excl_text, university_pathway_terms):
            matched = get_matched_terms(excl_text, below_university_only_terms)
            return True, f"below university level only (matched: {matched})"

    if contains_any(name, name_school_patterns):
        if not contains_any(excl_text, university_pathway_terms):
            matched = get_matched_terms(name, name_school_patterns)
            return True, f"below university level only (school name pattern: {matched})"


    if contains_any(excl_text, gymnasium_only_terms):
        if not contains_any(excl_text, university_pathway_terms):
            matched = get_matched_terms(excl_text, gymnasium_only_terms)
            return True, f"gymnasium only with no university pathway (matched: {matched})"

    user_text = normalize_text(user_purpose)
    if not contains_any(user_text, ["entrepren", "startup", "drivhus", "inkubat"]):
        if contains_any(excl_text, ENTREPRENEURSHIP_SUPPORT_TERMS):
            matched = get_matched_terms(excl_text, ENTREPRENEURSHIP_SUPPORT_TERMS)
            return True, f"entrepreneurship support (matched: {matched})"

    has_scholarship_terms = contains_any(excl_text, STRONG_DIRECT_SCHOLARSHIP_TERMS)

    if user_domain == "law":

        is_domain_scholarship = is_law_relevant(excl_text)
        if not is_domain_scholarship:

            non_law_matches = get_matched_terms(excl_text, NON_LAW_DOMAIN_TERMS)
            if len(non_law_matches) >= 2:
                matched = get_matched_terms(excl_text, NON_LAW_DOMAIN_TERMS)
                return True, f"non-law domain mismatch ({len(non_law_matches)} matches: {matched[:5]})"

            off_topic_single_terms = [
                "flyg", "rymd", "luftfart", "aviation", "aerospace",
                "restaurang", "livsmedel", "måltid", "matvetenskap",
                "romanska språk", "slaviska språk", "nordiska språk",
                "östasiatisk", "engelska språket", "germansk",
                "lingvistik", "språkvetenskap",
                "byggande", "boende", "samhällsbyggnad",
                "strukturell", "structural engineering",
                "idrott", "sport", "idrottsvetenskap",
                "sjöutbildning", "sjöingenjör", "sjökapten",
                "mode", "textil", "design",
                "omvårdnad", "sjukskötersk",
            ]
            if contains_any(excl_text, off_topic_single_terms):
                matched = get_matched_terms(excl_text, off_topic_single_terms)
                return True, f"off-topic subject for law user (matched: {matched[:3]})"

    if user_domain == "business":
        if contains_any(excl_text, LAW_TERMS) and not contains_any(excl_text, BUSINESS_TERMS):
            if _is_domain_specific(excl_text, LAW_TERMS):
                matched = get_matched_terms(excl_text, LAW_TERMS)
                return True, f"law domain mismatch - business user (matched: {matched})"
        if contains_any(excl_text, NON_BUSINESS_DOMAIN_TERMS) and not contains_any(excl_text, BUSINESS_TERMS):
            if _is_domain_specific(excl_text, NON_BUSINESS_DOMAIN_TERMS):
                if not has_scholarship_terms:
                    matched = get_matched_terms(excl_text, NON_BUSINESS_DOMAIN_TERMS)
                    return True, f"non-business domain mismatch (matched: {matched})"
                non_biz_count = count_matches(excl_text, NON_BUSINESS_DOMAIN_TERMS)
                biz_count = count_matches(excl_text, BUSINESS_TERMS)
                if non_biz_count > biz_count + 2:
                    matched = get_matched_terms(excl_text, NON_BUSINESS_DOMAIN_TERMS)
                    return True, f"non-business domain mismatch - primary domain (matched: {matched})"

    if user_domain == "technology":
        if contains_any(excl_text, NON_TECH_DOMAIN_TERMS) and not contains_any(excl_text, TECHNOLOGY_TERMS):
            if _is_domain_specific(excl_text, NON_TECH_DOMAIN_TERMS):
                if not has_scholarship_terms:
                    matched = get_matched_terms(excl_text, NON_TECH_DOMAIN_TERMS)
                    return True, f"non-tech domain mismatch (matched: {matched})"

    if user_domain == "medical":
        non_med_explicit = [
            "juridik", "juridisk", "juridiska", "affärsjuridik",
            "rättsvetenskap", "law", "legal",
            "sjörätt", "transporträtt", "folkrätt",
            "civilingenjör", "maskinteknik", "datateknik",
            "elektroteknik", "byggteknik", "programvaruteknik",
            "sjöbefäl", "sjöfart", "nautisk",
        ]
        if contains_any(excl_text, non_med_explicit) and not contains_any(excl_text, MEDICAL_TERMS):
            non_med_count = count_matches(excl_text, non_med_explicit)
            if non_med_count >= 2:
                matched = get_matched_terms(excl_text, non_med_explicit)
                return True, f"non-medical domain mismatch ({non_med_count} matches: {matched[:5]})"

        if contains_any(excl_text, NON_MEDICAL_DOMAIN_TERMS):
            non_med_count = count_matches(excl_text, NON_MEDICAL_DOMAIN_TERMS)
            if non_med_count >= 2:
                if has_scholarship_terms and non_med_count < 4:
                    pass
                else:
                    matched = get_matched_terms(excl_text, NON_MEDICAL_DOMAIN_TERMS)
                    return True, f"non-medical domain mismatch ({non_med_count} matches: {matched[:5]})"

    return False, ""


def should_exclude_study_level_mismatch(sch: Dict, user_purpose: str) -> Tuple[bool, str]:
    full_text = combined_scholarship_text(sch)
    purpose = scholarship_purpose_text(sch)
    excl_text = _exclusion_purpose_text(sch)
    classification = classify_scholarship(sch)

    is_undergrad_user = contains_any(normalize_text(user_purpose), UNDERGRAD_TERMS)
    _is_research_user = is_research_user(user_purpose)

    if is_undergrad_user and classification == "research":
        if is_domain_match(excl_text, user_purpose):
            
            return False, ""

        # Non-domain research scholarship for undergrad user
        if _has_research_and_education_coexistence(excl_text):
            return False, ""
        if _has_individual_grant_language(excl_text):
            return False, ""
        if is_strongly_student_facing(full_text):
            return False, ""

        if contains_any(excl_text, INDIVIDUAL_ACCESSIBLE_MARKERS):
            return False, ""

        return True, f"research-only scholarship for undergrad user (classification: research)"

    if _is_research_user and classification == "student":
        if is_domain_match(excl_text, user_purpose):
            return False, ""
        if is_faculty_wide_scholarship(full_text):
            return False, ""
        if has_thesis_student_terms(full_text):
            return False, ""

        undergrad_only_signals = [
            "gymnasieelever", "gymnasieelev",
            "grundskolan", "grundskoleelev",
            "årskurs 1", "årskurs 2", "årskurs 3",
            "lärjungar", "lärjunge",
            "elev vid borgarskolan", "elev vid",
        ]
        if contains_any(excl_text, undergrad_only_signals):
            matched = get_matched_terms(excl_text, undergrad_only_signals)
            return True, f"undergrad-only scholarship for research user (matched: {matched})"

        return False, ""

    return False, ""


def _is_domain_specific(text: str, domain_terms: List[str]) -> bool:
    t = normalize_text(text)
    match_count = sum(1 for term in domain_terms if term in t)
    return match_count >= 3


def _is_strongly_domain_specific(text: str, domain_terms: List[str]) -> bool:
    t = normalize_text(text)
    match_count = sum(1 for term in domain_terms if term in t)
    return match_count >= 5


def compute_entity_bonus(sch: Dict, user_purpose: str) -> float:
    bonus = 0.0
    text = combined_scholarship_text(sch)
    purpose = scholarship_purpose_text(sch)
    is_ug = contains_any(user_purpose, UNDERGRAD_TERMS)
    _is_res_user = is_research_user(user_purpose)
    classification = classify_scholarship(sch)

    if contains_any(user_purpose, BUSINESS_TERMS) and contains_any(text, BUSINESS_SCHOOL_STUDENT_TERMS):
        bonus += 0.35
    if contains_any(text, STRONG_DIRECT_SCHOLARSHIP_TERMS):
        bonus += 0.15
    if is_user_seeking_law(user_purpose) and is_law_relevant(text):
        bonus += 0.25
    if contains_any(user_purpose, BUSINESS_TERMS) and contains_any(text, BUSINESS_TERMS):
        bonus += 0.20
    if contains_any(user_purpose, TECHNOLOGY_TERMS) and contains_any(text, TECHNOLOGY_TERMS):
        bonus += 0.20
    if contains_any(user_purpose, MEDICAL_TERMS) and contains_any(text, MEDICAL_TERMS):
        bonus += 0.25

    if is_ug and classification == "student":
        bonus += 0.30
    elif is_ug and (is_strongly_student_facing(purpose) or is_strongly_student_facing(text)):
        bonus += 0.25

    if is_ug and is_strongly_student_facing(text) and is_domain_match(text, user_purpose):
        bonus += 0.20
    if is_ug and has_undergrad_indicators(text):
        bonus += 0.15

    if is_ug and classification == "research":
        bonus -= 0.35
    elif is_ug and classification == "mixed":
        bonus -= 0.10
    if is_ug and contains_any(text, ENTREPRENEURSHIP_SUPPORT_TERMS):
        bonus -= 0.50

    if _is_res_user:
        if classification == "research":
            bonus += 0.35
        elif classification == "mixed":
            bonus += 0.15
        elif classification == "student":
            bonus -= 0.15

        if is_research_beneficiary(purpose) or is_research_beneficiary(text):
            bonus += 0.15
        if has_research_study_level(sch):
            bonus += 0.10

    return round(bonus, 3)


def compute_soft_score(sch: Dict, purpose: str) -> float:
    ct = combined_scholarship_text(sch)
    pt = normalize_text(purpose)
    return round(((0.55 * fuzz.token_sort_ratio(pt, ct)) +
                  (0.45 * fuzz.partial_ratio(pt, ct))) / 100, 3)


def semantic_prefilter(sch: Dict, user_purpose: str) -> bool:
    score = sch.get("Adjusted Score", 0)
    text = combined_scholarship_text(sch)
    purpose = scholarship_purpose_text(sch)

    _is_res_user = is_research_user(user_purpose)

    if is_domain_match(text, user_purpose) and is_strongly_student_facing(text):
        return score >= 0.28
    if is_domain_match(text, user_purpose):
        return score >= 0.30 if _is_res_user else score >= 0.33

    if _is_res_user:
        cls = classify_scholarship(sch)
        if cls == "research":
            return score >= 0.30
        elif cls == "mixed":
            return score >= 0.33

    return score >= 0.38 if contains_any(user_purpose, UNDERGRAD_TERMS) else score >= 0.40


def llm_filter_scholarships(user_purpose, gender, scholarships, oai_client, debug=True):

    gender_rule = ""
    if gender and gender.lower() == "male":
        gender_rule = "\nGENDER RULE: User is male. Exclude scholarships explicitly for women only."
    elif gender and gender.lower() == "female":
        gender_rule = "\nGENDER RULE: User is female. Exclude scholarships explicitly for men only."

    is_undergrad = contains_any(user_purpose, UNDERGRAD_TERMS)
    _is_res_user = is_research_user(user_purpose)
    user_domain = get_user_domain(user_purpose)

    if is_undergrad:
        study_level_context = "The user is an UNDERGRADUATE student."
    elif _is_res_user:
        study_level_context = (
            "The user is a RESEARCHER (doctoral/postdoc/research level). "
            "PRIORITIZE research scholarships, research grants, forskarstipendier, "
            "doctoral funding, and postdoc positions. "
            "Include scholarships for 'forskning', 'vetenskaplig forskning', "
            "'doktorand', 'postdoc', 'forskare'. "
            "Student-only scholarships (grundnivå, bachelor) are LOWER priority "
            "but can still be included if domain-relevant."
        )
    else:
        study_level_context = "The user has NOT specified a study level -- treat all levels as eligible."

    domain_context = ""
    if user_domain == "business":
        domain_context = "BUSINESS USER: Include business, economics, finance, marketing, management, commerce, handelshogskolan. Exclude pure law, pure technology/engineering, medicine, music, arts."
    elif user_domain == "law":
        domain_context = "LAW USER: Include juridik, folkratt, EG-ratt, affarsjuridik, sjoratt, transportratt, rattsvetenskap. A law scholarship that mentions forskning alongside studerande is still valid. Exclude medicine, music, technology, natural sciences."
    elif user_domain == "technology":
        domain_context = "TECHNOLOGY USER: Include teknik, engineering, computer science, IT, software, electronics, civilingenjor. Exclude law, medicine, music, agriculture."
    elif user_domain == "medical":
        domain_context = "MEDICAL USER: Include medicin, medicine, healthcare, nursing, pharmacy, dental, biomedicin, klinisk forskning, karolinska, läkarutbildning. Exclude law, business, technology/engineering, music, arts."

    system_prompt = f"""You are a scholarship relevance filter. Your job is to decide which scholarships are relevant for this user.

USER PURPOSE: "{user_purpose}"
STUDY LEVEL CONTEXT: {study_level_context}

STEP 1 -- SUBJECT + STUDY LEVEL MATCH (Highest Priority)
First, identify scholarships that DIRECTLY match the user's subject AND study level.
These must be ranked and included first before anything else.

INCLUDE if the scholarship purpose:
  - Explicitly names the user's subject (e.g. law, economics, technology, engineering, medicine)
  - OR targets students at a relevant faculty, school, or university program
  - OR mentions the user's study level (bachelor, grundniva, kandidat, undergraduate, doctoral, postdoc)

RESEARCH LANGUAGE RULE -- CRITICAL:
  A scholarship may contain words like "forskning", "vetenskaplig", "utbildning och forskning".
  Do NOT auto-exclude these. Instead, ask: WHO receives the money?

  -> If it funds STUDENTS (studerande, elever, bachelor, kandidat, grundniva) -> INCLUDE for undergrad users
  -> If it funds RESEARCHERS only (forskare, postdoc, doktorand, PhD, dissertation) -> INCLUDE for research users, EXCLUDE for undergrad users
  -> If it funds BOTH students and researchers -> INCLUDE (dual-purpose is valid)
  -> If the purpose contains "grundutbildning" or "grundniva" -> ALWAYS INCLUDE for undergrad users

STUDY LEVEL EXCEPTION:
  If the user IS a researcher (PhD / postdoc / doctoral) -> also include research-primary scholarships. Prioritize research grants.
  If the user is UNDERGRADUATE -> exclude scholarships that are EXCLUSIVELY doctoral/postdoc with NO student component.

STEP 2 -- DOMAIN MATCH
After subject+level matches, evaluate domain fit.

{domain_context}

STEP 3 -- ENTITY TYPE CHECK
EXCLUDE these regardless of subject:
  - Funds for professorships, guest professorships, chairs, lectureships (not student-facing)
  - Institutional support funds with no direct applicant pathway
  - Funds that support only faculty/department operations

INCLUDE these even if they mention research:
  - Student union funds (studentkar)
  - Direct scholarships/stipendier to named student groups
  - Generic university scholarships open to all students
  - Business school student funds
  - Research grants and forskarstipendier (for research users){gender_rule}
STEP 4 -- DOUBT RULE
When uncertain:
  -> If it looks student-facing -> INCLUDE for undergrad users
  -> If it looks research-focused -> INCLUDE for research users
  -> If it looks institution/researcher-only -> EXCLUDE for undergrad users
  -> Generic scholarships with no subject restriction are valid for any student/researcher
N.B: Include Only those scholarships which are accurately mentioned users *SUBJECT*. Do not take any irrelevant subject scholarships.
Return ONLY a JSON array -- no text, no markdown:
[{{"index": 0, "relevance": "relevant"}}, {{"index": 1, "relevance": "irrelevant"}}]"""

    user_prompt = (
        f"Evaluate these scholarships for: \"{user_purpose}\"\n\n"
        "Scholarships:\n" +
        "\n".join([
            f"[{i}] {s['Name']}: {s['Purpose'][:200]}"
            for i, s in enumerate(scholarships)
        ]) +
        "\n\nReturn the JSON array now."
    )

    response = oai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    try:
        raw = response.choices[0].message.content.strip()
        start = raw.index("[")
        end = raw.rindex("]") + 1
        decisions = json.loads(raw[start:end])
        rel_indices = {d["index"] for d in decisions if d.get("relevance") == "relevant"}
        final_list = [scholarships[i] for i in sorted(rel_indices) if 0 <= i < len(scholarships)]

        if debug:
            excluded = [scholarships[i] for i in range(len(scholarships)) if i not in rel_indices]
            print(f"\n{'='*60}")
            print(f"[LLM FILTER] INCLUDED ({len(final_list)}):")
            print(f"{'='*60}")
            for s in final_list:
                cls = classify_scholarship(s)
                print(f"  [{cls:>8}] {s['Name']}")
                print(f"            Purpose: {s['Purpose'][:200]}")
                print(f"  {'-'*56}")
            print(f"\n{'='*60}")
            print(f"[LLM FILTER] EXCLUDED ({len(excluded)}):")
            print(f"{'='*60}")
            for s in excluded:
                cls = classify_scholarship(s)
                print(f"  [{cls:>8}] {s['Name']}")
                print(f"            Purpose: {s['Purpose'][:200]}")
                print(f"  {'-'*56}")

        return final_list
    except Exception as e:
        if debug:
            print(f"[LLM FILTER] FAILED: {e} -- returning all candidates unchanged")
        return scholarships


def rerank_with_llm(query, scholarships, oai_client, top_n=10, debug=True):
    is_undergrad = contains_any(query, UNDERGRAD_TERMS)
    _is_res_user = is_research_user(query)

    level_note = ""
    if is_undergrad:
        level_note = (
            "VIKTIGT: Användaren är undergraduate. "
            "Stipendier som riktar sig till STUDENTER ska rankas HÖGST. "
            "Stipendier med 'studerande'/'grundnivå'/'bachelor'/'kandidat' "
            "ska rankas före forskningsfokuserade stipendier.\n\n"
        )
    elif _is_res_user:
        level_note = (
            "VIKTIGT: Användaren söker FORSKNING/DOKTORAND-stipendier. "
            "Stipendier för forskning, doktorander, postdoc ska rankas HÖGST. "
            "Stipendier med 'forskning'/'vetenskaplig'/'doktorand'/'forskare' "
            "ska rankas före rena studentstipendier.\n\n"
        )

    formatted = "\n".join([
        f"{i+1}. {s['Name']}: {s['Purpose'][:150]}"
        for i, s in enumerate(scholarships)
    ])

    if _is_res_user:
        priority_order = (
            f"Prioriteringsordning:\n"
            f"1. Stipendier för forskning inom användarens ämnesområde (HÖGST)\n"
            f"2. Forskarstipendier och forskningsbidrag\n"
            f"3. Stipendier med forskningskomponent vid relevant fakultet/högskola\n"
            f"4. Blandade stipendier (forskning + utbildning)\n"
            f"5. Allmänna stipendier utan ämnesbegränsning (LÄGST)\n\n"
        )
    else:
        priority_order = (
            f"Prioriteringsordning:\n"
            f"1. Stipendier som nämner användarens ämne OCH riktar sig till studenter (HÖGST)\n"
            f"2. Stipendier till studerande vid relevant fakultet/högskola\n"
            f"3. Stipendier med studentnytta inom ämnesområdet\n"
            f"4. Studentkårsfonder och direkta bidrag\n"
            f"5. Allmänna stipendier utan ämnesbegränsning (LÄGST)\n\n"
        )

    prompt = (
        f"Rangordna dessa stipendier för användaren: \"{query}\".\n\n"
        f"{level_note}"
        f"{priority_order}"
        f"Returnera ENDAST en JSON-array: [3, 1, 2]\n\n"
        f"{formatted}"
    )
    response = oai_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a JSON-only responder. Output only a valid JSON array of integers."},
            {"role": "user", "content": prompt}
        ]
    )
    raw = response.choices[0].message.content.strip()
    try:
        start = raw.index("[")
        end = raw.rindex("]") + 1
        idx_list = json.loads(raw[start:end])
        ranked = [scholarships[i-1] for i in idx_list if 1 <= i <= len(scholarships)]

        if debug:
            print(f"\n{'='*60}")
            print(f"[LLM RERANK] Final Order (top {top_n}):")
            print(f"{'='*60}")
            for i, s in enumerate(ranked[:top_n]):
                cls = classify_scholarship(s)
                print(f"  {i+1}. [{cls:>8}] {s['Name']}")
                print(f"     Purpose: {s['Purpose'][:200]}")
                print(f"  {'-'*56}")

        return ranked[:top_n]
    except Exception as e:
        if debug:
            print(f"[LLM RERANK] FAILED: {e}")
        return scholarships[:top_n]


def find_scholarships_v2(user_purpose, gender=None, top_k=DEFAULT_TOP_K, debug=True, use_llm_rerank=True):
    _is_res_user = is_research_user(user_purpose)
    _is_ug_user = contains_any(user_purpose, UNDERGRAD_TERMS)

    if debug:
        print(f"\n{'#'*60}")
        print(f"# SEARCH: {user_purpose}")
        print(f"# Domain: {get_user_domain(user_purpose)}")
        print(f"# Undergrad: {_is_ug_user}")
        print(f"# Research User: {_is_res_user}")
        print(f"# Top-K: {top_k}")
        print(f"{'#'*60}")

    emb_query = expand_user_query_for_embedding(user_purpose)
    query_vector = openai_client.embeddings.create(
        model=EMBEDDING_MODEL, input=emb_query
    ).data[0].embedding
    res = index.query(vector=query_vector, top_k=top_k, include_metadata=True)

    initial_list = []
    for m in res.get("matches", []):
        md = m["metadata"]
        s = {
            "Name": md.get("Namn", ""),
            "Purpose": md.get("Ändamål", ""),
            "Study Level": md.get("Utbildningsnivå", ""),
            "Base Score": round(m["score"], 4)
        }
        for k, v in FIELD_MAP_SV.items():
            if k not in s:
                s[k] = md.get(v, "")
        s["Relevance Score"] = compute_soft_score(s, user_purpose)
        s["Entity Bonus"] = compute_entity_bonus(s, user_purpose)
        s["Adjusted Score"] = round(
            s["Base Score"] + s["Relevance Score"] + s["Entity Bonus"], 4
        )
        initial_list.append(s)

    if debug:
        print(f"\n{'='*60}")
        print(f"[PINECONE] Retrieved {len(initial_list)} candidates")
        print(f"{'='*60}")
    kept_rules = []
    excluded_rules = []

    for sch in initial_list:
        fail_entity, entity_reason = should_exclude_entity_type(sch, user_purpose)
        if fail_entity:
            excluded_rules.append((sch, entity_reason))
            continue

        fail_research, research_reason = should_exclude_research_doctoral(sch, user_purpose)
        if fail_research:
            cls = classify_scholarship(sch)
            excluded_rules.append((sch, f"Research Mismatch [{cls}] - {research_reason}"))
            continue

        fail_level, level_reason = should_exclude_study_level_mismatch(sch, user_purpose)
        if fail_level:
            excluded_rules.append((sch, f"Study Level Mismatch - {level_reason}"))
            continue

        kept_rules.append(sch)

    if debug:
        print(f"\n{'='*60}")
        print(f"[RULE PASS] INCLUDED ({len(kept_rules)}) | EXCLUDED ({len(excluded_rules)})")
        print(f"{'='*60}")
        for s in kept_rules:
            cls = classify_scholarship(s)
            dm = "[DOMAIN]" if is_domain_match(combined_scholarship_text(s), user_purpose) else "[GENERAL]"
            print(f"  [+] {dm} [{cls:>8}] {s['Name']}")
            print(f"      Purpose: {s['Purpose'][:150]}")
        print(f"\n  --- EXCLUDED ---")
        for s, reason in excluded_rules:
            print(f"  [-] {s['Name']} -> {reason}")
            print(f"      Purpose: {s['Purpose'][:150]}")

    kept_semantic = []
    excluded_semantic = []

    for sch in kept_rules:
        if semantic_prefilter(sch, user_purpose):
            kept_semantic.append(sch)
        else:
            excluded_semantic.append(sch)

    if debug:
        print(f"\n{'='*60}")
        print(f"[SEMANTIC PASS] INCLUDED ({len(kept_semantic)}) | EXCLUDED ({len(excluded_semantic)})")
        print(f"{'='*60}")
        for s in kept_semantic:
            cls = classify_scholarship(s)
            dm = "[DOMAIN]" if is_domain_match(combined_scholarship_text(s), user_purpose) else "[GENERAL]"
            print(f"  [+] {dm} [{cls:>8}] {s['Name']} [score={s['Adjusted Score']}]")
            print(f"      Purpose: {s['Purpose'][:150]}")
        print(f"\n  --- EXCLUDED ---")
        for s in excluded_semantic:
            print(f"  [-] {s['Name']} [score={s['Adjusted Score']}]")
            print(f"      Purpose: {s['Purpose'][:150]}")

    final_data = sorted(
        kept_semantic, key=lambda x: x["Adjusted Score"], reverse=True
    )[:MAX_CANDIDATES_FOR_LLM]

    if debug:
        print(f"\n{'='*60}")
        print(f"[PRE-LLM] Sending {len(final_data)} candidates to LLM filter")
        print(f"{'='*60}")

    if final_data:
        llm_filtered = llm_filter_scholarships(
            user_purpose, gender, final_data, openai_client, debug=debug
        )
        if len(llm_filtered) < MIN_RESULTS:
            if debug:
                print(f"\n[SAFETY NET] LLM returned only {len(llm_filtered)} -- padding to {MIN_RESULTS}")
            existing_names = {s["Name"] for s in llm_filtered}
            padding = [s for s in final_data if s["Name"] not in existing_names]
            final_data = llm_filtered + padding[:MIN_RESULTS - len(llm_filtered)]
        else:
            final_data = llm_filtered

    if use_llm_rerank and len(final_data) > 1:
        final_data = rerank_with_llm(
            user_purpose, final_data, openai_client, debug=debug
        )

    if debug:
        print(f"\n{'='*60}")
        print(f"[FINAL] Returning {len(final_data[:MIN_RESULTS])} results")
        print(f"{'='*60}")
        for i, s in enumerate(final_data[:MIN_RESULTS]):
            cls = classify_scholarship(s)
            print(f"  {i+1}. [{cls:>8}] {s['Name']}")
            print(f"     Purpose: {s['Purpose'][:200]}")

    return final_data[:MIN_RESULTS]


def run_single_audit(query: str, gender: str = None, debug: bool = False) -> Dict:
    results = find_scholarships_v2(query, gender=gender, debug=debug)
    audit = {
        "query": query,
        "gender": gender,
        "result_count": len(results),
        "results": []
    }
    for i, s in enumerate(results):
        text = combined_scholarship_text(s)
        cls = classify_scholarship(s)
        audit["results"].append({
            "rank": i + 1,
            "name": s.get("Name", ""),
            "purpose": s.get("Purpose", "")[:200],
            "base_score": s.get("Base Score", 0),
            "adjusted_score": s.get("Adjusted Score", 0),
            "classification": cls,
            "is_domain_specific": is_domain_match(text, query),
            "study_level": s.get("Study Level", ""),
        })
    return audit


def run_subject_audit(subject_label: str, query: str, gender: str = None, debug: bool = False):
    print(f"\n{'#'*70}")
    print(f"# AUDIT: {subject_label}")
    print(f"# Query: {query}")
    print(f"{'#'*70}")

    audit = run_single_audit(query, gender=gender, debug=debug)

    domain_count = sum(1 for r in audit["results"] if r["is_domain_specific"])
    student_count = sum(1 for r in audit["results"] if r["classification"] == "student")
    research_count = sum(1 for r in audit["results"] if r["classification"] == "research")
    mixed_count = sum(1 for r in audit["results"] if r["classification"] == "mixed")

    print(f"\nResults: {audit['result_count']} total")
    print(f"   Domain-specific: {domain_count}")
    print(f"   Student-facing: {student_count}")
    print(f"   Mixed: {mixed_count}")
    print(f"   Research-only: {research_count}")
    print()

    for r in audit["results"]:
        tag = "[DOMAIN]" if r["is_domain_specific"] else "[GENERAL]"
        cls_map = {
            "student": "[STUDENT]",
            "research": "[RESEARCH]",
            "mixed": "[MIXED]",
            "neutral": "[NEUTRAL]"
        }
        cls_tag = cls_map.get(r["classification"], "[NEUTRAL]")
        print(f"  {r['rank']:>2}. {tag}{cls_tag} [{r['adjusted_score']:.4f}] {r['name']}")
        print(f"      Level: {r['study_level']} | Class: {r['classification']}")
        print(f"      Purpose: {r['purpose']}")
        print()

    quality = min(100, int(
        (domain_count / max(audit["result_count"], 1)) * 30 +
        (student_count / max(audit["result_count"], 1)) * 30 +
        (mixed_count / max(audit["result_count"], 1)) * 10 +
        (40 if domain_count >= 1 and audit["results"][0].get("is_domain_specific") else 15) +
        (-20 * research_count / max(audit["result_count"], 1))
    ))
    print(f"  Estimated Quality Score: {quality}/100")
    audit["quality_score"] = quality
    return audit


def run_full_audit(queries: Dict[str, Dict] = None, debug: bool = False) -> Dict:
    if queries is None:
        queries = {
            "Technology": {"query": "Technology undergraduate scholarships in Sweden", "gender": None},
            "Business": {"query": "Business undergraduate scholarships in Sweden", "gender": None},
            "Law": {"query": "Law undergraduate scholarships in Sweden", "gender": None},
            "Medical": {"query": "Medical undergraduate scholarships in Sweden", "gender": None},
        }

    all_audits = {}
    for subject, params in queries.items():
        audit = run_subject_audit(
            subject, params["query"], params.get("gender"), debug=debug
        )
        all_audits[subject] = audit

    print(f"\n{'='*70}")
    print(f"  FULL AUDIT SUMMARY")
    print(f"{'='*70}")
    for subject, audit in all_audits.items():
        domain_count = sum(1 for r in audit["results"] if r["is_domain_specific"])
        student_count = sum(1 for r in audit["results"] if r["classification"] == "student")
        research_count = sum(1 for r in audit["results"] if r["classification"] == "research")
        mixed_count = sum(1 for r in audit["results"] if r["classification"] == "mixed")
        print(f"\n  {subject} -- Quality: {audit.get('quality_score', '?')}/100")
        print(f"     Domain: {domain_count} | Student: {student_count} | "
              f"Mixed: {mixed_count} | Research: {research_count}")
        for r in audit["results"]:
            tag = "[DOMAIN]" if r["is_domain_specific"] else "[GENERAL]"
            cls_map = {
                "student": "[STUDENT]",
                "research": "[RESEARCH]",
                "mixed": "[MIXED]",
                "neutral": "[NEUTRAL]"
            }
            cls_tag = cls_map.get(r["classification"], "[NEUTRAL]")
            print(f"     {r['rank']:>2}. {tag}{cls_tag} {r['name']}")
            print(f"         Purpose: {r['purpose']}")
    print(f"\n{'='*70}")
    return all_audits


def compare_audits(before: Dict, after: Dict):
    print(f"\n{'='*70}")
    print(f"  BEFORE / AFTER COMPARISON")
    print(f"{'='*70}")
    for subject in sorted(set(list(before.keys()) + list(after.keys()))):
        b = before.get(subject, {"results": [], "result_count": 0, "quality_score": 0})
        a = after.get(subject, {"results": [], "result_count": 0, "quality_score": 0})
        b_names = [r["name"] for r in b["results"]]
        a_names = [r["name"] for r in a["results"]]
        added = [n for n in a_names if n not in b_names]
        removed = [n for n in b_names if n not in a_names]
        kept = [n for n in a_names if n in b_names]

        print(f"\n  {subject}")
        print(f"     Quality: {b.get('quality_score', '?')}/100 -> {a.get('quality_score', '?')}/100")
        print(f"     Kept: {len(kept)} | Added: {len(added)} | Removed: {len(removed)}")
        if added:
            for n in added:
                print(f"       [+] {n}")
        if removed:
            for n in removed:
                print(f"       [-] {n}")
        if kept:
            changes = False
            for name in kept:
                b_rank = next((r["rank"] for r in b["results"] if r["name"] == name), "?")
                a_rank = next((r["rank"] for r in a["results"] if r["name"] == name), "?")
                if b_rank != a_rank:
                    if not changes:
                        print(f"     Rank Changes:")
                        changes = True
                    direction = "[UP]" if a_rank < b_rank else "[DOWN]"
                    print(f"       {direction} {name}: #{b_rank} -> #{a_rank}")
    print(f"\n{'='*70}")



def format_scholarship_json(scholarship_list, output_language="en"):
    formatted_list = []
    non_translatable = {
        "Email", "Website", "Phone", "Postal Code",
        "Epost", "Websida", "Telefon", "Postnr",
        "Municipality", "Kommun",
        "City", "Stad",
        "County", "Län",
        "Main Address", "Huvudadress",
    }
    for sch in scholarship_list:
        entry = {}
        for k, v in sch.items():
            if k in ["Base Score", "Relevance Score", "Entity Bonus", "Adjusted Score"]:
                continue
            final_k = FIELD_MAP_SV.get(k, k) if output_language.lower() == "sv" else k
            if k in non_translatable or not isinstance(v, str):
                entry[final_k] = v
            else:
                entry[final_k] = (
                    safe_translate(v, "sv", "en")
                    if output_language.lower() == "en"
                    else v
                )
        formatted_list.append(entry)
    return formatted_list

