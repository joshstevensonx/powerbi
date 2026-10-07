import zipfile, os, sys
src, out = sys.argv[1], sys.argv[2]
first = ["Version", "[Content_Types].xml", "DiagramLayout", "Settings", "Metadata", "Report/LinguisticSchema", "Connections"]
files = []
for root, _, fs in os.walk(src):
    for f in fs:
        files.append(os.path.relpath(os.path.join(root, f), src).replace(os.sep, "/"))
ordered = [f for f in first if f in files] + sorted(f for f in files if f not in first)
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for f in ordered:
        z.write(os.path.join(src, f), f)
print(len(ordered), "entries ->", out)
