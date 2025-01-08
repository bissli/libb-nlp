import os
from pathlib import Path


def download_spacy_model(model_name: str) -> None:
    """Download spaCy model if not already present"""
    import spacy

    # Special handling for frozen apps
    os.environ['SPACY_IS_COMPILED'] = 'true'
    os.environ['SPACY_DOWNLOAD_NO_RAISE'] = 'true'

    # Set up model cache directory in user's home
    cache_dir = Path.home() / '.cache' / 'libb-nlp' / 'spacy'
    os.makedirs(cache_dir, exist_ok=True)
    os.environ['SPACY_DATA_PATH'] = str(cache_dir)

    try:
        spacy.load(model_name)
    except (OSError, ImportError):
        print(f'Downloading spaCy model {model_name}...')
        from spacy.cli import download
        download(model_name, '--direct', '--no-deps', '--no-cache-dir')
        print('Download complete!')
        spacy.load(model_name)


def download_sentence_transformer(model_name: str):
    """Download and return sentence transformer model"""
    from sentence_transformers import SentenceTransformer

    # Set up model cache directory in user's home
    cache_dir = Path.home() / '.cache' / 'libb-nlp' / 'models'
    os.makedirs(cache_dir, exist_ok=True)
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
