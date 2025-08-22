
from sentence_transformers import SentenceTransformer
import os

def main():
    """
    This script pre-downloads and caches the sentence-transformer models
    required by the application to avoid download delays at runtime.
    """
    # The model required by KeyBERTExtractor
    model_name = "paraphrase-multilingual-MiniLM-L12-v2"
    
    print(f"[Model Pre-download] Caching model: {model_name}")
    
    try:
        # Instantiating the model triggers the download and caching process.
        SentenceTransformer(model_name)
        print(f"[Model Pre-download] Successfully cached {model_name}.")
    except Exception as e:
        print(f"[Model Pre-download] Error caching model {model_name}: {e}")
        # Exit with a non-zero code to fail the build process if download fails
        exit(1)

if __name__ == "__main__":
    main()

