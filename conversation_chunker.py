#!/usr/bin/env python3
"""
Conversation chunking for LLM analysis.

Splits long conversations into manageable chunks for analysis while
preserving natural boundaries (file operations, tool calls, task changes).
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
import re


@dataclass
class Chunk:
    """A chunk of conversation with metadata."""

    text: str
    start_char: int
    end_char: int
    chunk_index: int
    total_chunks: int
    boundary_reason: Optional[str] = None

    def __len__(self):
        """Return character count."""
        return len(self.text)


class ConversationChunker:
    """Splits conversations into chunks using natural boundaries."""

    # Target chunk size (characters)
    DEFAULT_CHUNK_SIZE = 150000  # ~200K tokens with prompt overhead
    MIN_CHUNK_SIZE = 50000  # Don't create tiny chunks

    def __init__(self, target_size: int = DEFAULT_CHUNK_SIZE, min_size: int = MIN_CHUNK_SIZE):
        """
        Initialize chunker.

        Args:
            target_size: Target chunk size in characters
            min_size: Minimum chunk size (avoid fragmentation)
        """
        self.target_size = target_size
        self.min_size = min_size

    def chunk(self, text: str, strategy: str = 'natural') -> List[Chunk]:
        """
        Split text into chunks.

        Args:
            text: Full conversation text
            strategy: Chunking strategy ('natural', 'fixed', 'sentences')

        Returns:
            List of Chunk objects
        """
        if len(text) <= self.target_size:
            # No chunking needed
            return [Chunk(
                text=text,
                start_char=0,
                end_char=len(text),
                chunk_index=0,
                total_chunks=1,
                boundary_reason='no_chunking_needed'
            )]

        if strategy == 'natural':
            return self._chunk_natural_boundaries(text)
        elif strategy == 'fixed':
            return self._chunk_fixed_size(text)
        elif strategy == 'sentences':
            return self._chunk_sentences(text)
        else:
            raise ValueError(f"Unknown chunking strategy: {strategy}")

    def _chunk_natural_boundaries(self, text: str) -> List[Chunk]:
        """
        Chunk on natural boundaries (file ops, tool calls, etc.).

        Strategy:
        1. Find all boundary positions
        2. Select boundaries near target size
        3. Create chunks with context
        """
        # Find all potential boundaries
        boundaries = self._find_boundaries(text)

        # Select optimal split points
        split_points = self._select_split_points(boundaries, len(text))

        # Create chunks
        chunks = []
        start = 0

        for i, end in enumerate(split_points):
            chunk_text = text[start:end]
            reason = boundaries.get(end, 'target_size_reached')

            chunks.append(Chunk(
                text=chunk_text,
                start_char=start,
                end_char=end,
                chunk_index=i,
                total_chunks=len(split_points),
                boundary_reason=reason
            ))

            start = end

        # Add final chunk if needed
        if start < len(text):
            chunks.append(Chunk(
                text=text[start:],
                start_char=start,
                end_char=len(text),
                chunk_index=len(chunks),
                total_chunks=len(chunks) + 1,
                boundary_reason='end_of_conversation'
            ))

        # Update total_chunks count
        for chunk in chunks:
            chunk.total_chunks = len(chunks)

        return chunks

    def _find_boundaries(self, text: str) -> dict:
        """
        Find all potential boundary positions in text.

        Returns:
            Dict mapping position -> boundary_reason
        """
        boundaries = {}

        # Pattern-based boundaries
        patterns = [
            # Tool results (end of tool execution)
            (r'</function_results>', 'tool_result_end'),
            # File operation markers
            (r'\nFile (?:created|updated|modified)', 'file_operation'),
            # Test execution markers
            (r'(?:tests? (?:passing|failing|complete))', 'test_execution'),
            # Explicit task transitions
            (r'(?:Next|Now|Okay),? (?:let\'s|I\'ll)', 'task_transition'),
            # Double newlines (paragraph breaks)
            (r'\n\n+', 'paragraph_break'),
        ]

        for pattern, reason in patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                pos = match.end()
                # Prefer more specific reasons
                if pos not in boundaries:
                    boundaries[pos] = reason

        return boundaries

    def _select_split_points(self, boundaries: dict, text_length: int) -> List[int]:
        """
        Select optimal split points from boundary candidates.

        Strategy:
        - Target chunks of target_size
        - Prefer boundaries near target positions
        - Ensure minimum chunk size
        """
        split_points = []
        current_pos = 0
        sorted_boundaries = sorted(boundaries.keys())

        while current_pos < text_length:
            target_pos = current_pos + self.target_size

            if target_pos >= text_length:
                # Last chunk
                break

            # Find boundary closest to target_pos
            best_boundary = self._find_nearest_boundary(
                sorted_boundaries,
                target_pos,
                current_pos,
                text_length
            )

            if best_boundary:
                split_points.append(best_boundary)
                current_pos = best_boundary
            else:
                # No good boundary, use target_pos
                split_points.append(target_pos)
                current_pos = target_pos

        return split_points

    def _find_nearest_boundary(
        self,
        boundaries: List[int],
        target: int,
        min_pos: int,
        max_pos: int
    ) -> Optional[int]:
        """
        Find boundary nearest to target position within constraints.

        Args:
            boundaries: Sorted list of boundary positions
            target: Target position
            min_pos: Minimum position (enforce minimum chunk size)
            max_pos: Maximum position (text length)

        Returns:
            Best boundary position or None
        """
        # Filter boundaries within valid range
        min_boundary = min_pos + self.min_size
        max_boundary = min(target + (self.target_size // 2), max_pos)

        valid_boundaries = [
            b for b in boundaries
            if min_boundary <= b <= max_boundary
        ]

        if not valid_boundaries:
            return None

        # Return boundary closest to target
        return min(valid_boundaries, key=lambda b: abs(b - target))

    def _chunk_fixed_size(self, text: str) -> List[Chunk]:
        """Simple fixed-size chunking (fallback)."""
        chunks = []
        start = 0
        index = 0

        while start < len(text):
            end = min(start + self.target_size, len(text))
            chunks.append(Chunk(
                text=text[start:end],
                start_char=start,
                end_char=end,
                chunk_index=index,
                total_chunks=0,  # Will update after
                boundary_reason='fixed_size'
            ))
            start = end
            index += 1

        # Update total_chunks
        for chunk in chunks:
            chunk.total_chunks = len(chunks)

        return chunks

    def _chunk_sentences(self, text: str) -> List[Chunk]:
        """Chunk on sentence boundaries (more conservative)."""
        # Simple sentence detection
        sentences = re.split(r'(?<=[.!?])\s+', text)

        chunks = []
        current_chunk = []
        current_size = 0
        start_pos = 0

        for sentence in sentences:
            sentence_size = len(sentence)

            if current_size + sentence_size > self.target_size and current_size >= self.min_size:
                # Finish current chunk
                chunk_text = ' '.join(current_chunk)
                chunks.append(Chunk(
                    text=chunk_text,
                    start_char=start_pos,
                    end_char=start_pos + len(chunk_text),
                    chunk_index=len(chunks),
                    total_chunks=0,
                    boundary_reason='sentence_boundary'
                ))

                start_pos += len(chunk_text) + 1  # +1 for space
                current_chunk = []
                current_size = 0

            current_chunk.append(sentence)
            current_size += sentence_size

        # Add final chunk
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            chunks.append(Chunk(
                text=chunk_text,
                start_char=start_pos,
                end_char=start_pos + len(chunk_text),
                chunk_index=len(chunks),
                total_chunks=0,
                boundary_reason='end_of_conversation'
            ))

        # Update total_chunks
        for chunk in chunks:
            chunk.total_chunks = len(chunks)

        return chunks


def create_chunker(target_size: int = 150000) -> ConversationChunker:
    """
    Factory function to create a chunker.

    Args:
        target_size: Target chunk size in characters

    Returns:
        ConversationChunker instance
    """
    return ConversationChunker(target_size=target_size)
