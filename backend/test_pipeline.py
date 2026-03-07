from document_pipeline.pipeline import process_dataset

if __name__ == "__main__":
    events = process_dataset("../dataset/text.data.jsonl", limit=5)

    for e in events:
        print(e)