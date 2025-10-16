import os
from pathlib import Path


def download_spacy_model(model_name: str) -> None:
    """Download spaCy model if not already present"""
    import spacy

    # Set up model cache directory in user's home
    cache_dir = Path.home() / '.cache' / 'libb-nlp' / 'spacy'
    Path(cache_dir).mkdir(exist_ok=True, parents=True)
    os.environ['SPACY_DATA_PATH'] = str(cache_dir)

    try:
        # Try to load the model first
        spacy.load(model_name)
    except (OSError, ImportError):
        print(f'Downloading spaCy model {model_name}...')
        # Use spacy.cli.download() directly
        from spacy.cli import download
        download(model_name)
        print('Download complete!')
        spacy.load(model_name)  # Verify the model loads


def download_sentence_transformer(model_name: str):
    """Download and return sentence transformer model"""
    from sentence_transformers import SentenceTransformer

    # Set up model cache directory in user's home
    cache_dir = Path.home() / '.cache' / 'libb-nlp' / 'models'
    Path(cache_dir).mkdir(exist_ok=True, parents=True)
    os.environ['SENTENCE_TRANSFORMERS_HOME'] = str(cache_dir)

    # Initialize model with download handling
    try:
        tokenizer_kwargs = {'clean_up_tokenization_spaces': True}
        model = SentenceTransformer(model_name, tokenizer_kwargs=tokenizer_kwargs)
    except OSError:
        print(f'Downloading sentence-transformers model {model_name}... This will only happen once.')
        model = SentenceTransformer(model_name, tokenizer_kwargs=tokenizer_kwargs)
        print('Download complete!')
    return model
