import asyncio
import logging

import torch
from lnlp.splitters import TextSplitterSimilarity, TextSplitterSpacy

logger = logging.getLogger(__name__)


class SplitterManager:
    """Manages text splitter instances and their lifecycle."""

    def __init__(self):
        self._spacy_splitter: TextSplitterSpacy | None = None
        self._similarity_splitter: TextSplitterSimilarity | None = None
        self._lock = asyncio.Lock()
        self.model_stats = {
            'spacy_calls': 0,
            'similarity_calls': 0,
            'last_spacy_error': None,
            'last_similarity_error': None
        }

    async def get_spacy_splitter(self) -> TextSplitterSpacy:
        """Get or initialize spaCy splitter instance."""
        if self._spacy_splitter is None:
            async with self._lock:
                if self._spacy_splitter is None:
                    try:
                        self._spacy_splitter = await asyncio.to_thread(TextSplitterSpacy)
                        logger.info('Initialized spaCy splitter')
                    except Exception as e:
                        self.model_stats['last_spacy_error'] = str(e)
                        logger.error(f'Failed to initialize spaCy splitter: {e}')
                        raise
        self.model_stats['spacy_calls'] += 1
        return self._spacy_splitter

    async def get_similarity_splitter(self) -> TextSplitterSimilarity:
        """Get or initialize similarity splitter instance."""
        if self._similarity_splitter is None:
            async with self._lock:
                if self._similarity_splitter is None:
                    try:
                        self._similarity_splitter = await asyncio.to_thread(TextSplitterSimilarity)
                        logger.info('Initialized similarity splitter')
                    except Exception as e:
                        self.model_stats['last_similarity_error'] = str(e)
                        logger.error(f'Failed to initialize similarity splitter: {e}')
                        raise
        self.model_stats['similarity_calls'] += 1
        return self._similarity_splitter

    async def health_check(self) -> dict:
        """Check health status of splitter instances."""
        status = {
            'spacy': {
                'loaded': self._spacy_splitter is not None,
                'calls': self.model_stats['spacy_calls'],
                'last_error': self.model_stats['last_spacy_error']
            },
            'similarity': {
                'loaded': self._similarity_splitter is not None,
                'calls': self.model_stats['similarity_calls'],
                'last_error': self.model_stats['last_similarity_error'],
                'gpu_available': torch.cuda.is_available() if self._similarity_splitter else None
            }
        }
        return status

    async def cleanup(self):
        """Cleanup resources during shutdown."""
        logger.info('Cleaning up splitter manager resources')
        # Currently no cleanup needed, but framework is in place
        self._spacy_splitter = None
        self._similarity_splitter = None
