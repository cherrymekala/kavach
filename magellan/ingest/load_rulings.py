"""Load cleaned rulings (JSONL) into a Vertex AI Search data store.

Each line: {"id", "country", "insurer", "category", "decision", "summary", "text"}
TODO(week 2): implement with google-cloud-discoveryengine DocumentServiceClient.import_documents.
"""
