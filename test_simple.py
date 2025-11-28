# Simple test - run: python Folder/manage.py shell then: exec(open('test_simple.py', encoding='utf-8').read())

from documents.models import Document
from documents.detectors import AdvancedPlagiarismDetector

print("=" * 60)
print("QUICK TEST")
print("=" * 60)

docs = Document.objects.all().order_by('-id')[:2]

if len(docs) < 2:
    print("Need at least 2 documents")
    exit(1)

doc1, doc2 = docs[0], docs[1]

print(f"\nDoc1: ID={doc1.id}, name='{doc1.name}', on_defense={doc1.on_defense}, user={doc1.user_id}")
print(f"Doc2: ID={doc2.id}, name='{doc2.name}', on_defense={doc2.on_defense}, user={doc2.user_id}")

print("\n" + "=" * 60)
print("TEST 1: Check doc1")
print("=" * 60)

detector = AdvancedPlagiarismDetector()
result1 = detector.detect_plagiarism(doc1.id)

print(f"Originality: {result1['originality']}%")
print(f"Status: {result1['status']}")
print(f"Message: {result1['message']}")
print(f"Similar docs found: {len(result1.get('similar_documents', []))}")

if result1.get('source_matches'):
    print(f"File name duplicates: {len(result1['source_matches'])}")

print("\n" + "=" * 60)
print("TEST 2: Check doc2")
print("=" * 60)

result2 = detector.detect_plagiarism(doc2.id)

print(f"Originality: {result2['originality']}%")
print(f"Status: {result2['status']}")
print(f"Message: {result2['message']}")
print(f"Similar docs found: {len(result2.get('similar_documents', []))}")

if result2.get('source_matches'):
    print(f"File name duplicates: {len(result2['source_matches'])}")

print("\n" + "=" * 60)
print("ANALYSIS")
print("=" * 60)

if doc1.data and doc2.data:
    name1 = doc1.data.name.split('/')[-1] if '/' in doc1.data.name else doc1.data.name
    name2 = doc2.data.name.split('/')[-1] if '/' in doc2.data.name else doc2.data.name
    print(f"Doc1 file name: {name1}")
    print(f"Doc2 file name: {name2}")
    
    if name1 == name2:
        print("WARNING: File names MATCH - doc2 should show 0% if doc1 on defense")
    else:
        print("OK: File names are DIFFERENT")

print(f"\nDocuments on defense: {Document.objects.filter(on_defense=True).count()}")
print(f"Documents NOT on defense: {Document.objects.filter(on_defense=False).count()}")

print("\n" + "=" * 60)
print("EXPECTED:")
print("=" * 60)
print("1. If file names match AND doc1 on defense -> doc2 should show 0%")
print("2. If file names different -> normal text analysis")
print("3. Compare only with on_defense=True documents")
print("4. User documents also compared between themselves")
print("=" * 60)

