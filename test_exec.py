import sys
with open('test_exec_output.txt', 'w') as f:
    f.write("Python executed successfully!\n")
    f.write(f"Python version: {sys.version}\n")
