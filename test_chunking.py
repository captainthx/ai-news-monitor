text = "A" * 3000 + "\n" + "B" * 2000
max_len = 4000
chunks = []
current_chunk = ""
for line in text.split("\n"):
    if len(current_chunk) + len(line) + 1 > max_len:
        chunks.append(current_chunk.strip())
        current_chunk = line + "\n"
    else:
        current_chunk += line + "\n"
        
if current_chunk.strip():
    chunks.append(current_chunk.strip())

print([len(c) for c in chunks])
