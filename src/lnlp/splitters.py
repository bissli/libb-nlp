import math
import os
import warnings
from abc import ABC, abstractmethod

import numpy as np
import regex as re
from langchain.text_splitter import SpacyTextSplitter
from lnlp.downloaders import download_sentence_transformer
from lnlp.downloaders import download_spacy_model

__all__ = [
    'TextSplitterSpacy',
    'TextSplitterSimilarity',
]

# Performance optimizations
# os.environ['SPACY_DISABLE_GPU_VALIDATION'] = 'true'
os.environ['SPACY_SKIP_GLOBS'] = '*.so,*.dll,*.pyi'


class BaseTextSplitter(ABC):

    @abstractmethod
    def split_text(self, text: str) -> list[str]:
        """Splitter returns a list of chunked strings
        """


class TextSplitterSpacy(BaseTextSplitter):
    """Basic token size splitter that breaks on sentences using LangChain's SpacyTextSplitter.
    """

    def __init__(self, model_name='en_core_web_sm'):
        """Initialize the text chunker with spacy model name.
        """
        download_spacy_model(model_name)
        self.splitter = SpacyTextSplitter(pipeline=model_name)

    def split_text(self, text: str, chunk_size: int = 4000, chunk_overlap: int = 200) -> list[str]:
        r"""Break text into chunks of approximately max_chunk_size characters,
        respecting sentence boundaries using LangChain's SpacyTextSplitter.

        >>> chunker = TextSplitterSpacy()
        >>> text = ("Thanks, Ray. Good morning and thank you for joining us to discuss our results. Let me begin by"
        ... " thanking the employees across Winnebago Industries and our portfolio of outdoor recreation brands for their"
        ... " hard work and resilience throughout the year. Although a difficult retail environment made fiscal 2024 a"
        ... " challenging year for the RV and Marine industries, the collaborative culture and commitment to excellence at"
        ... " Grand Design, Winnebago Newmar, Barletta, Chris-Craft and Lithionics, all serve as the foundation for a return"
        ... " to growth as market conditions improve in the future. Before we get into the details of our Q4 and full year"
        ... " results, there are several key messages I want to convey on this morning's call. First, while the retail"
        ... " environment remains challenging in the short term, we anticipate gradual market improvement over the next 12 to"
        ... " 15 months. We would expect this to occur more materially as we move into the second quarter of calendar 2025,"
        ... " our third fiscal quarter, factoring in the projected easing of interest rates and decreased inventory levels in"
        ... " the Motorhome RV category. Second, we have made substantive leadership changes at Winnebago Motorhome and"
        ... " Winnebago Towables to remedy the operational and financial challenges that have affected the performance of"
        ... " those businesses in recent quarters. Third, we are delighted by the enthusiastic consumer and dealer response"
        ... " to the Lineage Series M Grand Design's inaugural entry in the Motorhome RV segment. The new vehicle was"
        ... " featured at last month's Hershey RV show and RV dealer Open House, and a small number of units began shipping"
        ... " in Q4. The Grand Design team, with support from the businesses across our portfolio, have created an RV with"
        ... " benefits that we believe set a new standard for excellence in a Class C coach. And finally, today we are"
        ... " providing annual financial guidance for the first time. In light of the continued market uncertainty, we are"
        ... " being appropriately cautious out of the gate, but at the midpoint we are forecasting modest improvement on the"
        ... " top line and adjusted EPS growth of 10% compared to prior year.")
        >>> chunks = chunker.split_text(text, chunk_size=500, chunk_overlap=0)
        >>> print(f"Number of chunks: {len(chunks)}")
        Number of chunks: 6
        >>> for i, chunk in enumerate(chunks, 1):
        ...     print(f"Chunk {i}:{chunk[:70]}...")
        Chunk 1:Thanks, Ray. Good morning and thank you for joining us to discuss our ...
        Chunk 2:Although a difficult retail environment made fiscal 2024 a challenging...
        Chunk 3:First, while the retail environment remains challenging in the short t...
        Chunk 4:Second, we have made substantive leadership changes at Winnebago Motor...
        Chunk 5:The new vehicle was featured at last month's Hershey RV show and RV de...
        Chunk 6:In light of the continued market uncertainty, we are being appropriate...
        """
        self.splitter._chunk_size = chunk_size
        self.splitter._chunk_overlap = chunk_overlap
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            return [s.replace('\n\n', ' ') for s in self.splitter.split_text(text)]


class TextSplitterSimilarity(BaseTextSplitter):
    """Text chunker that chunks based on cosine similarity.
    """

    def __init__(self, model_name='all-mpnet-base-v2'):
        """Initialize text chunking class
        Args:
            model_name (str): Name of sentence transformer model to use
        """
        import pysbd

        self.model_name = model_name
        self.seg = pysbd.Segmenter(language='en', clean=False)
        self._model = None  # Defer loading

    @property
    def model(self):
        """Lazy load the model only when needed"""
        if self._model is None:
            self._model = download_sentence_transformer(self.model_name)
        return self._model

    def _rev_sigmoid(self, x:float)->float:
        """Reversed sigmoid function"""
        return (1 / (1 + math.exp(0.5*x)))

    def _activate_similarities(self, similarities:np.array, p_size=10)->np.array:
        """Function returns list of weighted sums of activated sentence similarities
        Args:
            similarities (numpy array): square matrix where each sentence corresponds to another with cosine similarity
            p_size (int): number of sentences used to calculate weighted sum
        Returns:
            list: list of weighted sums
        """
        # If text is too short, return array of zeros
        if similarities.shape[0] <= p_size:
            return np.zeros(similarities.shape[0])

        # Create weights for sigmoid function
        x = np.linspace(-10,10,p_size)
        y = np.vectorize(self._rev_sigmoid)
        activation_weights = np.pad(y(x),(0,similarities.shape[0]-p_size))

        # Take each diagonal to the right of the main diagonal
        diagonals = [similarities.diagonal(each) for each in range(similarities.shape[0])]

        # Pad each diagonal with zeros at the end
        diagonals = [np.pad(each, (0,similarities.shape[0]-len(each))) for each in diagonals]

        # Stack diagonals into new matrix
        diagonals = np.stack(diagonals)

        # Apply activation weights to each row
        diagonals *= activation_weights.reshape(-1, 1)

        # Calculate weighted sum of activated similarities
        activated_similarities = np.sum(diagonals, axis=0)

        return activated_similarities

    def _process_text(self, text: str):
        """Process text and return sentences, similarities, activated
        similarities and minimas

        Args:
            text (str): Input text to process
        Returns:
            tuple: (sentences, similarities, activated_similarities, minimas)
        """
        from scipy.signal import argrelextrema
        from sklearn.metrics.pairwise import cosine_similarity

        # Replace newlines
        text = re.sub(r'[\n\r]', '', text).strip()

        # Split text into sentences using pysbd
        sentences = self.seg.segment(text)

        # Split into sentences again
        sentences = text.split('. ')

        # Get embeddings
        embeddings = self.model.encode(sentences)

        # Normalize embeddings
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings /= norms

        # Calculate similarities
        similarities = cosine_similarity(embeddings)

        # Get activated similarities
        activated_similarities = self._activate_similarities(similarities, p_size=10)

        # Find relative minima
        minimas = argrelextrema(activated_similarities, np.less, order=2)

        return sentences, similarities, activated_similarities, minimas

    def split_text(self, text: str) -> list[str]:
        r"""Split text into paragraphs using sentence embeddings and similarity
        Args:
            text (str): Input text to split
        Returns:
            list[str]: List of text chunks split into paragraphs

        >>> chunker = TextSplitterSimilarity()
        >>> text = ("Thanks, Ray. Good morning and thank you for joining us to discuss our results. Let me begin by"
        ... " thanking the employees across Winnebago Industries and our portfolio of outdoor recreation brands for their"
        ... " hard work and resilience throughout the year. Although a difficult retail environment made fiscal 2024 a"
        ... " challenging year for the RV and Marine industries, the collaborative culture and commitment to excellence at"
        ... " Grand Design, Winnebago Newmar, Barletta, Chris-Craft and Lithionics, all serve as the foundation for a return"
        ... " to growth as market conditions improve in the future. Before we get into the details of our Q4 and full year"
        ... " results, there are several key messages I want to convey on this morning's call. First, while the retail"
        ... " environment remains challenging in the short term, we anticipate gradual market improvement over the next 12 to"
        ... " 15 months. We would expect this to occur more materially as we move into the second quarter of calendar 2025,"
        ... " our third fiscal quarter, factoring in the projected easing of interest rates and decreased inventory levels in"
        ... " the Motorhome RV category. Second, we have made substantive leadership changes at Winnebago Motorhome and"
        ... " Winnebago Towables to remedy the operational and financial challenges that have affected the performance of"
        ... " those businesses in recent quarters. Third, we are delighted by the enthusiastic consumer and dealer response"
        ... " to the Lineage Series M Grand Design's inaugural entry in the Motorhome RV segment. The new vehicle was"
        ... " featured at last month's Hershey RV show and RV dealer Open House, and a small number of units began shipping"
        ... " in Q4. The Grand Design team, with support from the businesses across our portfolio, have created an RV with"
        ... " benefits that we believe set a new standard for excellence in a Class C coach. And finally, today we are"
        ... " providing annual financial guidance for the first time. In light of the continued market uncertainty, we are"
        ... " being appropriately cautious out of the gate, but at the midpoint we are forecasting modest improvement on the"
        ... " top line and adjusted EPS growth of 10% compared to prior year.")
        >>> chunks = chunker.split_text(text)
        >>> print(f"Number of chunks: {len(chunks)}")
        Number of chunks: 2
        >>> for i, chunk in enumerate(chunks, 1):
        ...     print(f"Chunk {i}:{chunk[:70]}...")
        Chunk 1:Thanks, Ray. Good morning and thank you for joining us to discuss our ...
        Chunk 2:First, while the retail environment remains challenging in the short t...
        """
        # Process text and get required data
        sentences, _, activated_similarities, minimas = self._process_text(text)

        # Create chunks based on split points
        split_points = list(minimas[0])
        chunks = []
        current_chunk = []

        for num, each in enumerate(sentences):
            # Add period if sentence doesn't end with one
            sentence = each if each.endswith('.') else f'{each}.'
            current_chunk.append(sentence)

            if num in split_points:
                chunks.append((' '.join(current_chunk)).strip())
                current_chunk = []

        # Add any remaining sentences in the last chunk
        if current_chunk:
            chunks.append((' '.join(current_chunk)).strip())

        return chunks

    def plot_similarities(self, text:str):
        """Plot the similarities and split points for a given text
        Args:
            text (str): Input text to analyze and plot
        """
        import matplotlib.pyplot as plt
        import seaborn as sns

        # Process text and get required data
        _, _, activated_similarities, minimas = self._process_text(text)

        fig, ax = plt.subplots()
        sns.lineplot(y=activated_similarities, x=range(len(activated_similarities)), ax=ax)
        plt.vlines(x=minimas, ymin=min(activated_similarities),
                   ymax=max(activated_similarities), colors='purple', ls='--',
                   lw=1)
        plt.title('Paragraph Split Points')
        plt.show()


if __name__ == '__main__':
    __import__('doctest').testmod(optionflags=4 | 8 | 32)
