import logging
import operator
import re
import statistics
from collections import defaultdict
from io import BytesIO
from statistics import mean, stdev

import pdfplumber

logger = logging.getLogger(__name__)


def fmt_default(lines: list[dict], **kwargs) -> str:
    """Convert structured text data into HTML with consistent styling.

    lines:
        Required:
            - text (str): The text content to format
            - type (str): Content type ('text', 'break', 'page_number', etc)
        Optional:
            - heading_level (int): 1-6 for heading levels
            - bold (bool): Whether text should be bold
            - italic (bool): Whether text should be italic
            - spacing_after (float): Vertical spacing after in points
            - font_size (float): Font size in points
            - weight (int): Font weight (400=normal, 700=bold)
            - classes (list): Additional CSS classes to apply
            - style (dict): Additional CSS styles as key-value pairs

    kwargs:
        max_margin (float): Maximum margin-bottom in points (default: 15.)
        paragraph_spacing (float): Extra spacing between paragraphs (default: 1.5)
        line_height (float): Line height multiplier (default: 1.2)
        font_family (str): Default font family (default: None)
        text_align (str): Default text alignment (default: None)
        color_scheme (dict): Colors for different elements (default: {})
        custom_classes (list): Additional CSS classes to apply (default: [])
        style_overrides (dict): CSS properties to override defaults (default: {})
        custom_tags (dict): Mapping of content types to HTML tags (default: None)

    Returns
        str: HTML formatted text with appropriate styling
    """
    # extract formatting options from kwargs with defaults
    max_margin = kwargs.get('max_margin', 15.)
    paragraph_spacing = kwargs.get('paragraph_spacing', 1.5)
    line_height = kwargs.get('line_height', 1.2)
    font_family = kwargs.get('font_family')
    text_align = kwargs.get('text_align')
    color_scheme = kwargs.get('color_scheme', {})
    custom_classes = kwargs.get('custom_classes', [])
    style_overrides = kwargs.get('style_overrides', {})

    # set up HTML structure
    html_parts = []
    default_tags = {'break': 'div', 'page_number': 'div', 'text': 'div', 'list': 'ul'}
    tags = {**default_tags, **(kwargs.get('custom_tags') or {})}

    for line in lines:
        if not line:
            continue

        line_type = line.get('type', 'text')

        if line_type == 'break':
            html_parts.append('<div class="paragraph-break">&nbsp;</div>')
            continue

        if line_type == 'list':
            # Handle list with items
            style_attrs = []
            if 'spacing_after' in line and line['spacing_after'] > 0:
                margin = min(line['spacing_after'], max_margin)
                style_attrs.append(f'margin-bottom: {margin}pt')
            style_str = f' style="{"; ".join(style_attrs)}"' if style_attrs else ''

            html_parts.append(f'<ul{style_str}>')
            for item in line['items']:
                item_classes = []
                if item.get('bold'):
                    item_classes.append('bold')
                if item.get('italic'):
                    item_classes.append('italic')

                class_str = f' class="{" ".join(item_classes)}"' if item_classes else ''
                html_parts.append(f'<li{class_str}>{item["text"]}</li>')
            html_parts.append('</ul>')
            continue

        style_attrs = []
        if 'spacing_after' in line and line['spacing_after'] > 0:
            margin = min(line['spacing_after'], max_margin)
            style_attrs.append(f'margin-bottom: {margin}pt')
        if 'weight' in line:
            style_attrs.append(f'font-weight: {line["weight"]}')
        if 'style' in line:
            style_attrs.extend(f'{k}: {v}' for k, v in line['style'].items())
        classes = []
        if line.get('bold'):
            classes.append('bold')
        if line.get('italic'):
            classes.append('italic')
        if line.get('underline'):
            classes.append('underline')
        if line.get('classes'):
            classes.extend(line['classes'])
        if line_type == 'page_number':
            classes.append('page-number')
        attrs = []
        if classes:
            attrs.append(f'class="{" ".join(classes)}"')
        if style_attrs:
            attrs.append(f'style="{"; ".join(style_attrs)}"')
        if line.get('heading_level'):
            tag = f'h{line["heading_level"]}'
        else:
            tag = tags.get(line_type, 'div')
        attrs_str = f' {" ".join(attrs)}' if attrs else ''
        html_parts.append(f'<{tag}{attrs_str}>{line["text"]}</{tag}>')

    return '\n'.join(html_parts)


class PDFTextExtractor:
    """Extract and analyze text content from PDF files."""

    # Class constants for thresholds
    HEADER_THRESHOLD = 0.12  # top 12% of page
    FOOTER_THRESHOLD = 0.88  # bottom 12% of page
    MIN_REPETITION_RATIO = 0.25  # minimum ratio of pages where text must appear
    POSITION_VARIANCE_THRESHOLD = 0.015  # maximum allowed variance in positions
    CLUSTERING_THRESHOLD = 0.02  # maximum distance for position clustering
    MIN_CLUSTER_SIZE = 2  # minimum number of items to form a cluster

    PAGE_NUMBER_PATTERNS = [
        r'^\d+$',
        r'^Page\s+\d+$',
        r'^\d+\s+of\s+\d+$',
        r'^-\s*\d+\s*-$',
        r'^\[\s*\d+\s*\]$',  # [42]
        r'^p\.\s*\d+$',      # p. 42
        r'^.*Page\s+\d+\s+of\s+\d+.*$',  # matches "Page X of Y" anywhere in line
        r'^.*Printed\s+on\s+\d{2}-\d{2}-\d{4}\s+Page\s+\d+\s+of\s+\d+.*$',  # matches "Printed on" format
        r'.*\bpage\s+\d+\b.*$',  # matches "page N" anywhere in line (case insensitive)
    ]

    HEADER_PATTERNS = [
        r'^Chapter\s+\d+',
        r'^Section\s+\d+',
        r'^\w+\s+\d{4}$',    # date-like headers
        r'^[A-Z\s]{10,}$',   # all caps text
        r'^[\w\s-]+\s*[-–]\s*\d+$',  # title - 42
        r'^\d+\s*[-–]\s*[\w\s-]+$',  # 42 - Title
        r'^[A-Z][a-z]+\s+\d{1,2},\s+\d{4}$',  # date formats
    ]

    FOOTER_PATTERNS = [
        r'.*Copyright\s*©?\s*\d{4}.*',  # copyright © 2024 anywhere in line
        r'.*©\s*\d{4}.*',               # © 2024 Company anywhere in line
        r'.*\bAll\s+[Rr]ights\s+[Rr]eserved\b.*',
        r'.*\bConfidential\b.*',
        r'.*\bDraft\s+Version\b.*',
        r'.*\bRev(?:ision)?\.?\s*\d+.*',
        r'.*\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}\b.*',  # date formats anywhere
        r'.*\bProprietary\b.*',         # proprietary notices
        r'.*\bConfidential\b.*',        # confidential notices
        r'.*\bCopyright\b.*\d{4}.*',    # copyright YYYY in any order
        r'.*\bRestricted\b.*',          # restricted notices
        r'.*\bInternal\s+Use\s+Only\b.*'  # internal Use Only
    ]

    def __init__(self, pdf_input, **kwargs):
        """Initialize the PDF text extractor.

        Args:
            pdf_input: Either a file path (str) or PDF content (bytes)
            **kwargs: Configuration overrides
                header_threshold: Override HEADER_THRESHOLD
                footer_threshold: Override FOOTER_THRESHOLD
                min_repetition_ratio: Override MIN_REPETITION_RATIO
                clustering_threshold: Override CLUSTERING_THRESHOLD
                min_cluster_size: Override MIN_CLUSTER_SIZE
        """
        # Document-wide analysis results
        self.doc_metrics = None  # Will store baseline metrics
        self.doc_flow = None     # Will store document flow analysis
        self.style_patterns = {}  # Will store detected style patterns

        if isinstance(pdf_input, bytes):
            self.pdf_input = BytesIO(pdf_input)
        if isinstance(pdf_input, str):
            self.pdf_input = pdf_input

        self.repeated_lines = defaultdict(list)
        self.page_heights = []
        self.font_stats = defaultdict(list)

        # allow configuration override
        self.config = {
            'header_threshold': kwargs.get('header_threshold', self.HEADER_THRESHOLD),
            'footer_threshold': kwargs.get('footer_threshold', self.FOOTER_THRESHOLD),
            'min_repetition_ratio': kwargs.get('min_repetition_ratio', self.MIN_REPETITION_RATIO),
            'clustering_threshold': kwargs.get('clustering_threshold', self.CLUSTERING_THRESHOLD),
            'min_cluster_size': kwargs.get('min_cluster_size', self.MIN_CLUSTER_SIZE)
        }

    def _analyze_document_metrics(self, pdf):
        """Analyze document-wide metrics"""
        metrics = {
            'pages': len(pdf.pages),
            'dimensions': [],
            'fonts': defaultdict(list),
            'positions': defaultdict(list),
            'baseline': {
                'font_size': None,
                'line_height': None,
                'paragraph_spacing': None,
                'margins': None
            }
        }

        # Gather page-level metrics
        margin_lefts = []
        margin_rights = []
        line_heights = []
        paragraph_spacings = []
        font_sizes = []

        for page in pdf.pages:
            metrics['dimensions'].append((page.width, page.height))

            elements = page.extract_words(
                keep_blank_chars=True,
                use_text_flow=True,
                extra_attrs=['fontname', 'size', 'weight']
            )

            if not elements:
                continue

            # Track margins
            lefts = [elem['x0'] for elem in elements]
            rights = [elem['x1'] for elem in elements]
            margin_lefts.append(min(lefts))
            margin_rights.append(page.width - max(rights))

            # Track line heights and paragraph spacing
            sorted_elems = sorted(elements, key=operator.itemgetter('top', 'x0'))
            prev_bottom = None
            line_top = sorted_elems[0]['top']
            line_elements = []

            for elem in sorted_elems:
                if prev_bottom is not None:
                    gap = elem['top'] - prev_bottom
                    if gap > 0:
                        if gap > page.height * 0.02:  # Paragraph break threshold
                            if line_elements:
                                paragraph_spacings.append(gap)
                        else:
                            line_heights.append(gap)

                if abs(elem['top'] - line_top) > 3:  # New line
                    line_top = elem['top']
                    line_elements = []
                line_elements.append(elem)
                prev_bottom = elem['bottom']

            # Track font metrics
            for elem in elements:
                metrics['fonts'][elem.get('fontname')].append({
                    'size': elem.get('size'),
                    'weight': elem.get('weight', 400),
                    'text': elem.get('text')
                })
                metrics['positions'][elem.get('top')/page.height].append(elem)
                if elem.get('size'):
                    font_sizes.append(elem['size'])

        # Calculate baseline metrics
        metrics['baseline'] = self._calculate_baseline_metrics(
            font_sizes, line_heights, paragraph_spacings,
            margin_lefts, margin_rights
        )

        return metrics

    def _cluster_positions(self, positions: list[float], threshold: float) -> list[list[float]]:
        """Cluster positions that are close together.

        Args:
            positions: List of positions to cluster
            threshold: Maximum distance between positions in same cluster

        Returns
            List of clusters, where each cluster is a list of positions
        """
        if not positions:
            return []

        # sort positions
        sorted_pos = sorted(positions)
        clusters = [[sorted_pos[0]]]

        # group positions into clusters
        for pos in sorted_pos[1:]:
            if pos - clusters[-1][-1] <= threshold:
                clusters[-1].append(pos)
            else:
                clusters.append([pos])

        return clusters

    def clean_text(self, text: str) -> str:
        """Clean extracted text while preserving meaningful whitespace"""
        text = re.sub(r'[\u200b\u200c\u200d\ufeff]', ' ', text)
        text = text.replace('"', '"').replace('"', '"').replace('—', '-')
        # only collapse multiple spaces within lines, not line endings
        text = re.sub(r'[ \t]+', ' ', text)
        return text.rstrip()

    def _detect_footers(self, pages: list[pdfplumber.page.Page]) -> set[str]:
        """
        Detect footers using multiple heuristics:
        1. Consistent vertical position
        2. Consistent font/size
        3. Regular repetition across pages
        4. Position at bottom of page
        5. Special handling for page numbers
        """
        footers = set()
        text_positions = self._analyze_vertical_positions(pages)
        total_pages = len(pages)

        # regular expression for page numbers
        page_number_pattern = re.compile(r'^\d+$|^Page\s+\d+$|^\d+\s+of\s+\d+$')

        for text, positions in text_positions.items():
            if len(positions) < total_pages * self.config['min_repetition_ratio']:
                continue

            bottom_positions = [pos['top'] for pos in positions]

            if len(bottom_positions) > 1:
                pos_mean = mean(bottom_positions)
                pos_std = stdev(bottom_positions)

                is_page_number = bool(page_number_pattern.match(text))
                position_threshold = self.config['footer_threshold'] if not is_page_number else 0.95

                # stricter checks for copyright/footer text
                is_copyright = any(re.search(pattern, text, re.IGNORECASE)
                                   for pattern in self.FOOTER_PATTERNS)

                position_consistency = pos_std < (0.008 if is_copyright else 0.015)
                position_requirement = pos_mean > (0.93 if is_copyright else position_threshold)

                if (position_requirement and
                    position_consistency and
                        len({pos['font'] for pos in positions}) == 1):

                    # additional check for page numbers
                    if is_page_number:
                        page_numbers = sorted(pos['page'] for pos in positions)
                        if self._validate_page_numbers(page_numbers):
                            footers.add(text)
                    else:
                        footers.add(text)

        return footers

    def _detect_headers(self, pages: list[pdfplumber.page.Page]) -> set[str]:
        """Detect headers using multiple heuristics"""
        headers = set()
        text_positions = self._analyze_vertical_positions(pages)
        total_pages = len(pages)

        for text, positions in text_positions.items():
            # Only consider as running header if:
            # 1. Appears on multiple pages
            # 2. Consistently at the very top
            # 3. Same font across appearances
            if len(positions) >= 2:  # Multiple appearances
                top_positions = [pos['top'] for pos in positions]
                pos_mean = mean(top_positions)
                pos_std = stdev(top_positions) if len(top_positions) > 1 else 0

                # Must appear at very top of multiple pages to be a running header
                if (pos_mean < self.config['header_threshold'] * 0.3 and  # Very top of page
                    pos_std < self.POSITION_VARIANCE_THRESHOLD * 0.25 and  # Very consistent position
                        len({pos['font'] for pos in positions}) == 1):  # Same font
                    headers.add(text)

        return headers

    def _analyze_document_flow(self, pdf):
        """Analyze overall document structure and flow"""
        flow = {
            'sections': [],
            'hierarchy': defaultdict(list),
            'styles': defaultdict(list),
            'patterns': {
                'headings': [],
                'lists': [],
                'paragraphs': []
            }
        }

        # First pass - gather metrics
        for page in pdf.pages:
            elements = self._extract_page_elements(page)
            self._analyze_page_flow(elements, flow)

        # Second pass - detect patterns
        self._detect_section_patterns(flow)
        self._detect_style_patterns(flow)

        return flow

    def _analyze_page_flow(self, elements, flow):
        """Analyze single page flow and patterns"""
        # Group elements by vertical position
        y_positions = defaultdict(list)
        for elem in elements:
            y_positions[elem['relative']['position']].append(elem)

        # Analyze position patterns
        for y, elems in y_positions.items():
            pattern = {
                'position': y,
                'style': self._get_dominant_style(elems),
                'indent': statistics.mean(e['relative']['indent'] for e in elems),
                'count': len(elems)
            }
            flow['patterns']['paragraphs'].append(pattern)

        # Detect potential headings
        for elem in elements:
            if self._is_potential_heading(elem):
                flow['patterns']['headings'].append(elem)

    def _detect_section_patterns(self, flow):
        """Detect section boundaries and hierarchy"""
        sections = []
        current_section = None

        for pattern in flow['patterns']['paragraphs']:
            if self._is_section_break(pattern):
                if current_section:
                    sections.append(current_section)
                current_section = {
                    'start': pattern['position'],
                    'style': pattern['style'],
                    'elements': []
                }
            elif current_section:
                current_section['elements'].append(pattern)

        flow['sections'] = sections

    def _detect_style_patterns(self, flow):
        """Detect consistent style patterns"""
        # Analyze heading styles
        heading_styles = defaultdict(list)
        for heading in flow['patterns']['headings']:
            key = self._get_style_key(heading['style'])
            heading_styles[key].append(heading)

        # Find dominant patterns
        flow['styles']['headings'] = self._get_dominant_patterns(heading_styles)

        # Similar analysis for other content types
        flow['styles']['body'] = self._analyze_body_styles(flow)
        flow['styles']['lists'] = self._analyze_list_styles(flow)

    def _analyze_style_signals(self, group):
        """Analyze style-based classification signals"""
        return {
            'emphasis': self._calculate_emphasis_score(group),
            'consistency': self._calculate_style_consistency(group),
            'distinctiveness': self._calculate_style_distinctiveness(group),
            'relative_metrics': {
                'size': group['style']['relative_size'],
                'weight': group['style']['weight'] / 400,  # Normalize to regular weight
                'indent': group['position']['indent']
            }
        }

    def _analyze_position_signals(self, group):
        """Analyze position-based classification signals"""
        return {
            'vertical_gap': self._calculate_vertical_gap(group),
            'alignment': self._detect_alignment(group),
            'indentation': self._analyze_indentation(group),
            'column_position': self._detect_column_position(group)
        }

    def _analyze_content_signals(self, group):
        """Analyze content-based classification signals"""
        text = group['text']
        return {
            'length': len(text),
            'word_count': len(text.split()),
            'case_pattern': self._analyze_case_pattern(text),
            'punctuation': self._analyze_punctuation(text),
            'numbering': self._detect_numbering(text),
            'special_markers': self._detect_special_markers(text)
        }

    def _analyze_context_signals(self, group):
        """Analyze context-based classification signals"""
        return {
            'section_position': self._get_section_position(group),
            'nearby_elements': self._analyze_nearby_elements(group),
            'content_flow': self._analyze_content_flow(group),
            'semantic_role': self._detect_semantic_role(group)
        }

    def _determine_content_type(self, signals):
        """Determine content type using multiple signals"""
        # Calculate scores for each type
        scores = {
            'heading': self._calculate_heading_score(signals),
            'list_item': self._calculate_list_score(signals),
            'paragraph': self._calculate_paragraph_score(signals),
            'table_cell': self._calculate_table_score(signals),
            'caption': self._calculate_caption_score(signals)
        }

        # Get type with highest score
        content_type = max(scores.items(), key=operator.itemgetter(1))[0]

        # Add subtype if applicable
        if content_type == 'heading':
            level = self._determine_heading_level(signals)
            return f'heading{level}'

        return content_type

    def _format_heading(self, item):
        """Format heading with appropriate level and style"""
        level = int(item['type'].replace('heading', ''))
        style = []

        if item['style']['emphasis']:
            style.append('bold')

        if item['style']['relative_size'] > 1.2:
            style.append(f"font-size: {item['style']['relative_size']}em")

        style_str = f' class="{" ".join(style)}"' if style else ''

        return f'<h{level}{style_str}>{item["text"]}</h{level}>'

    def _format_list_item(self, item):
        """Format list item with appropriate style"""
        style = []
        if item['style']['emphasis']:
            style.append('bold')

        style_str = f' class="{" ".join(style)}"' if style else ''

        return f'<li{style_str}>{item["text"]}</li>'

    def _format_text(self, item):
        """Format regular text with style"""
        style = []

        # Add emphasis
        if item['style']['emphasis']:
            style.append('bold')

        # Add spacing
        if 'spacing_after' in item:
            style.append(f"margin-bottom: {item['spacing_after']}pt")

        style_str = f' style="{"; ".join(style)}"' if style else ''

        return f'<div{style_str}>{item["text"]}</div>'

    def _analyze_vertical_positions(self, pages: list[pdfplumber.page.Page]) -> dict[str, list[float]]:
        """Analyze vertical positions and font characteristics of text across all pages"""
        positions = defaultdict(list)

        def cluster_positions(positions: list[float]) -> list[list[float]]:
            """Cluster similar vertical positions together using dynamic thresholds"""
            if not positions:
                return []

            positions = sorted(positions)

            # calculate dynamic threshold based on page height
            avg_height = mean(self.page_heights)
            dynamic_threshold = min(
                self.config['clustering_threshold'],
                (15 / avg_height)  # approximately 15 points in PDF units
            )

            clusters = [[positions[0]]]
            cluster_stats = [(positions[0], 0)]  # (mean, std_dev)

            for pos in positions[1:]:
                # find best matching cluster
                best_cluster_idx = None
                min_distance = float('inf')

                for idx, (cluster_mean, cluster_std) in enumerate(cluster_stats):
                    distance = abs(pos - cluster_mean)
                    if distance < min_distance and distance < (dynamic_threshold + cluster_std):
                        min_distance = distance
                        best_cluster_idx = idx

                if best_cluster_idx is not None:
                    clusters[best_cluster_idx].append(pos)
                    # update cluster statistics
                    new_mean = mean(clusters[best_cluster_idx])
                    new_std = stdev(clusters[best_cluster_idx]) if len(clusters[best_cluster_idx]) > 1 else 0
                    cluster_stats[best_cluster_idx] = (new_mean, new_std)
                else:
                    clusters.append([pos])
                    cluster_stats.append((pos, 0))

            return [c for c in clusters if len(c) >= self.config['min_cluster_size']]

        for page_num, page in enumerate(pages, 1):
            self.page_heights.append(page.height)
            words = page.extract_words(
                keep_blank_chars=True,
                use_text_flow=True,
                extra_attrs=['fontname', 'size', 'upright', 'stroking_color', 'non_stroking_color']
            )

            for word in words:
                text = word['text']
                relative_top = word['top'] / page.height
                font_info = (word['fontname'], word['size'])

                # track font usage statistics
                self.font_stats[font_info].append({
                    'text': text,
                    'position': relative_top,
                    'page': page_num
                })

                positions[text].append({
                    'top': relative_top,
                    'page': page_num,
                    'font': font_info,
                    'size': word['size'],
                    'cluster': None  # will be set during clustering
                })

        # perform clustering on positions
        for text, pos_list in positions.items():
            tops = [p['top'] for p in pos_list]
            clusters = cluster_positions(tops)

            # assign cluster IDs to positions
            for pos in pos_list:
                for i, cluster in enumerate(clusters):
                    if abs(pos['top'] - mean(cluster)) < self.config['clustering_threshold']:
                        pos['cluster'] = i
                        break

        return positions

    def _validate_page_numbers(self, page_numbers: list[int]) -> bool:
        """Validate if the sequence represents legitimate page numbers"""
        if not page_numbers:
            return False

        # check if numbers are in sequence (allowing for some gaps)
        gaps = [page_numbers[i+1] - page_numbers[i]
                for i in range(len(page_numbers)-1)]

        return all(1 <= gap <= 3 for gap in gaps)

    def detect_headers_footers(self, pages: list[pdfplumber.page.Page]) -> tuple[set[str], set[str]]:
        """Main method to detect both headers and footers"""
        headers = self._detect_headers(pages)
        footers = self._detect_footers(pages)

        # remove any overlapping detections
        footers -= headers

        return headers, footers

    def _analyze_font_style(self, word):
        """Analyze font properties to determine text style"""
        font_name = word.get('fontname', '').lower()

        # common font weight indicators
        bold_indicators = {'bold', 'heavy', 'black', 'extra', 'demi'}
        # common style indicators
        italic_indicators = {'italic', 'oblique', 'slanted'}
        # common decorative indicators
        decorative = {'underline', 'strikethrough', 'strike'}

        # detect weight
        is_bold = any(indicator in font_name for indicator in bold_indicators)
        # some fonts use numbers for weight (e.g., 700 = bold)
        if not is_bold and 'weight' in word:
            is_bold = int(word.get('weight', 400)) >= 700

        style = {
            'bold': is_bold,
            'italic': any(indicator in font_name for indicator in italic_indicators),
            'underline': any(indicator in font_name for indicator in decorative),
            'font': font_name,
            'weight': word.get('weight', 400)  # default weight is 400
        }
        return style

    def _determine_heading_level(self, word_group) -> int | None:
        """Determine heading level based on font properties"""
        if not word_group:
            return None

        # get style of first word as representative
        style = self._analyze_font_style(word_group[0])

        # heading detection logic based on font weight and name
        font_name = style['font'].lower()

        if 'heading1' in font_name or ('black' in font_name and style['bold']):
            return 1
        elif 'heading2' in font_name or ('extra' in font_name and style['bold']):
            return 2
        elif 'heading3' in font_name or ('heavy' in font_name and style['bold']):
            return 3
        elif style['bold']:
            return 4
        return None

    def _is_list_item(self, text: str, indent: float, page_width: float) -> bool:
        """Determine if text is likely a list item based on formatting"""
        return (
            # Indented from left margin
            indent > page_width * 0.1 and
            # Not a full-width paragraph
            len(text.split()) < 20 and
            # Check for bullet points or similar indentation/formatting
            bool(text.strip())
        )

    def _calculate_line_spacing(self, words: list) -> list:
        """Calculate vertical spacing between lines of text"""
        if not words:
            return []

        # calculate base font size for relative sizing
        font_sizes = [w.get('size', 0) for w in words]
        base_font_size = mean(font_sizes) if font_sizes else 12

        # sort words by vertical position
        sorted_words = sorted(words, key=operator.itemgetter('top', 'x0'))
        line_groups = []
        current_group = [sorted_words[0]]
        last_bottom = sorted_words[0]['bottom']

        # group words into lines
        for word in sorted_words[1:]:
            if abs(word['top'] - current_group[0]['top']) <= 3:  # same line threshold
                current_group.append(word)
            else:
                spacing = word['top'] - last_bottom
                heading_level = self._determine_heading_level(current_group)

                # analyze styles for the group
                styles = [self._analyze_font_style(w) for w in current_group]
                is_bold = all(s['bold'] for s in styles)
                is_italic = all(s['italic'] for s in styles)

                # get font size directly from words since it's not in styles
                font_sizes = [w.get('size', 12) for w in current_group]
                avg_font_size = mean(font_sizes) if font_sizes else 12

                line_groups.append({
                    'words': current_group,
                    'spacing_after': spacing,
                    'top': current_group[0]['top'],
                    'heading_level': heading_level,
                    'bold': is_bold,
                    'italic': is_italic,
                    'font_size': avg_font_size
                })
                current_group = [word]
                last_bottom = word['bottom']

        # add final group
        if current_group:
            styles = [self._analyze_font_style(w) for w in current_group]
            heading_level = self._determine_heading_level(current_group)
            font_sizes = [w.get('size', 12) for w in current_group]
            avg_font_size = mean(font_sizes) if font_sizes else 12

            line_groups.append({
                'words': current_group,
                'spacing_after': 0,
                'top': current_group[0]['top'],
                'heading_level': heading_level,
                'bold': all(s['bold'] for s in styles),
                'italic': all(s['italic'] for s in styles),
                'font_size': avg_font_size
            })

        return line_groups

    def extract_lines(self, include_page_numbers=False) -> list:
        """Main method to extract and clean text from PDF, returning list of lines
        """
        extracted_lines = []
        last_y_position = None

        with pdfplumber.open(self.pdf_input) as pdf:
            headers, footers = self.detect_headers_footers(pdf.pages)

            for page_num, page in enumerate(pdf.pages, 1):
                words = page.extract_words(
                    keep_blank_chars=True,
                    use_text_flow=True,
                    x_tolerance=1,
                    y_tolerance=3
                )

                if not words:
                    continue

                if include_page_numbers:
                    extracted_lines.append(f'Page {page_num}')

                line_groups = self._calculate_line_spacing(words)

                for group in line_groups:
                    # combine words in the line
                    line_text = ' '.join(w['text'] for w in group['words'])
                    line_text = self.clean_text(line_text)

                    if line_text \
                        and not any(header in line_text for header in headers) \
                        and not any(footer in line_text for footer in footers) \
                        and not any(re.search(pattern, line_text, re.IGNORECASE) for pattern in self.FOOTER_PATTERNS) \
                        and (include_page_numbers or not any(re.match(pattern, line_text, re.IGNORECASE) for pattern in self.PAGE_NUMBER_PATTERNS)) \
                        and len(line_text) > 1:

                        # only add newline for significant paragraph breaks
                        if last_y_position is not None:
                            spacing = group['top'] - last_y_position
                            if spacing > page.height * 0.06:  # ~6% of page height
                                extracted_lines.extend(('', line_text))
                            else:
                                # append to previous line if it exists and not a significant break
                                if extracted_lines and extracted_lines[-1]:
                                    extracted_lines[-1] = extracted_lines[-1] + ' ' + line_text
                                else:
                                    extracted_lines.append(line_text)
                        else:
                            extracted_lines.append(line_text)
                        last_y_position = group['top']

                # reset position tracking between pages
                last_y_position = None
                extracted_lines.append('')

        return [line for line in extracted_lines if line is not None]

    def extract_text(self, include_page_numbers=False):
        """Main extraction method"""
        content = []

        with pdfplumber.open(self.pdf_input) as pdf:
            # First detect headers/footers
            headers, footers = self.detect_headers_footers(pdf.pages)

            for page_num, page in enumerate(pdf.pages, 1):
                logger.debug(f'Processing page {page_num}')

                # Extract words with all needed properties
                words = page.extract_words(
                    keep_blank_chars=True,
                    use_text_flow=True,
                    x_tolerance=1,
                    y_tolerance=3,
                    extra_attrs=['fontname', 'size', 'weight', 'upright']
                )

                if not words:
                    continue

                # Process page content
                page_content = self._process_page_content(
                    words,
                    page,
                    headers,
                    footers,
                    include_page_numbers
                )

                content.extend(page_content)

        return self._format_content(content)

    def _process_page_content(self, words, page, headers, footers, include_page_numbers):
        """Process page content preserving structure"""
        content = []
        current_line = []
        last_y = None

        for word in words:
            # Skip headers/footers
            if self._is_header_footer(word['text'], headers, footers):
                continue

            # Check for new line
            if last_y is not None and abs(word['top'] - last_y) > 3:
                if current_line:
                    line = self._process_line(current_line, page)
                    if line:
                        content.append(line)
                current_line = []

            current_line.append(word)
            last_y = word['top']

        # Process final line
        if current_line:
            line = self._process_line(current_line, page)
            if line:
                content.append(line)

        return content

    def _process_line(self, words, page):
        """Process line with context from document metrics"""
        if not words:
            return None

        text = ' '.join(w['text'] for w in words)
        if not text.strip():
            return None

        # Use baseline metrics for relative measurements
        font_sizes = [w.get('size', 0) for w in words]
        avg_size = statistics.mean(font_sizes)
        relative_size = avg_size / self.doc_metrics['baseline']['font_size']

        # Calculate spacing relative to baseline
        spacing_after = self._get_spacing_after(words[-1], page)
        relative_spacing = spacing_after / self.doc_metrics['baseline']['line_height']

        # Calculate indentation relative to baseline
        indent = words[0].get('x0', 0) - self.doc_metrics['baseline']['margins']['left']
        relative_indent = indent / page.width

        props = {
            'text': text,
            'type': 'text',
            'style': {
                'font_size': avg_size,
                'relative_size': relative_size,
                'weight': max(w.get('weight', 400) for w in words),
                'relative_indent': relative_indent,
                'relative_spacing': relative_spacing
            }
        }

        # Use relative metrics for classification
        if relative_size > 1.2 or props['style']['weight'] >= 700:
            props['type'] = 'heading'
            props['heading_level'] = self._get_heading_level(props)
        elif relative_indent > 0.1:
            props['type'] = 'list_item'

        return props

    def _is_bold(self, words):
        """Detect bold text using multiple signals"""
        for word in words:
            # Check font name
            font_name = word.get('fontname', '').lower()
            if any(indicator in font_name
                   for indicator in ['bold', 'heavy', 'black']):
                return True

            # Check weight
            if word.get('weight', 400) >= 700:
                return True

        return False

    def _get_heading_level(self, props):
        """Determine heading level"""
        if props['weight'] >= 800:
            return 1
        if props['weight'] >= 700:
            return 2
        return 3

    def _get_spacing_after(self, word, page):
        """Calculate spacing after line"""
        try:
            return word.get('bottom', 0) - word.get('top', 0)
        except:
            return 0

    def _is_header_footer(self, text, headers, footers):
        """Check if text is header/footer"""
        return text in headers or text in footers

    def _format_content(self, content):
        """Format content as HTML"""
        html = []

        for item in content:
            if item['type'] == 'heading':
                html.append(
                    f'<h{item["heading_level"]} style="margin-bottom: {item["spacing_after"]}pt">'
                    f'{item["text"]}'
                    f'</h{item["heading_level"]}>'
                )
            else:
                html.append(
                    f'<div style="margin-bottom: {item["spacing_after"]}pt">'
                    f'{item["text"]}'
                    '</div>'
                )

        return '\n'.join(html)

    def extract_html(self, formatter=fmt_default, include_page_numbers=False) -> str:
        """Extract text and format as HTML with custom formatting

        Args:
            formatter: Function to convert structured text data to HTML.
                     Must accept list of dicts with text metadata and return HTML string.
                     Defaults to fmt_default.
            include_page_numbers: Whether to include page number markers

        Returns
            String containing HTML formatted text with appropriate styling
        """
        extracted_lines = []
        in_list = False
        current_list_items = []
        last_indent = None

        with pdfplumber.open(self.pdf_input) as pdf:
            headers, footers = self.detect_headers_footers(pdf.pages)

            for page_num, page in enumerate(pdf.pages, 1):
                words = page.extract_words(
                    keep_blank_chars=True,
                    use_text_flow=True,
                    x_tolerance=1,
                    y_tolerance=3,
                    extra_attrs=['fontname', 'size']
                )

                if include_page_numbers:
                    extracted_lines.append({
                        'text': f'Page {page_num}',
                        'type': 'page_number'
                    })

                if not words:
                    continue

                line_groups = self._calculate_line_spacing(words)

                for group in line_groups:
                    line_text = ' '.join(w['text'] for w in group['words'])
                    line_text = self.clean_text(line_text)

                    # skip headers, footers and empty lines without adding breaks
                    if line_text in headers \
                        or line_text in footers \
                        or any(re.search(pattern, line_text, re.IGNORECASE) for pattern in self.FOOTER_PATTERNS) \
                        or any(re.match(pattern, line_text, re.IGNORECASE) for pattern in self.PAGE_NUMBER_PATTERNS) \
                        or not line_text:
                        continue

                    # Get indentation level
                    current_indent = group['words'][0].get('x0', 0)

                    # Check if this is a list item
                    is_list_item = self._is_list_item(line_text, current_indent, page.width)

                    if is_list_item:
                        if not in_list:
                            in_list = True
                        current_list_items.append({
                            'text': line_text,
                            'spacing_after': group['spacing_after'],
                            'bold': group['bold'],
                            'italic': group['italic']
                        })
                    else:
                        # If we were in a list and hit non-list content, close the list
                        if in_list and current_list_items:
                            extracted_lines.append({
                                'type': 'list',
                                'items': current_list_items,
                                'spacing_after': current_list_items[-1]['spacing_after']
                            })
                            current_list_items = []
                            in_list = False

                        # Regular text handling
                        if group['spacing_after'] > page.height * 0.06 or \
                           group['heading_level'] or \
                           (extracted_lines and extracted_lines[-1].get('heading_level')):
                            extracted_lines.append({
                                'text': line_text,
                                'type': 'text',
                                'heading_level': group['heading_level'],
                                'bold': group['bold'],
                                'italic': group['italic'],
                                'spacing_after': group['spacing_after']
                            })
                        else:
                            # append to previous text if it exists
                            if extracted_lines and extracted_lines[-1]['type'] == 'text':
                                extracted_lines[-1]['text'] += ' ' + line_text
                            else:
                                extracted_lines.append({
                                    'text': line_text,
                                    'type': 'text',
                                    'heading_level': group['heading_level'],
                                    'bold': group['bold'],
                                    'italic': group['italic'],
                                    'spacing_after': group['spacing_after']
                                })

        # Handle any remaining list items at end of document
        if current_list_items:
            extracted_lines.append({
                'type': 'list',
                'items': current_list_items,
                'spacing_after': current_list_items[-1]['spacing_after']
            })

        return formatter(extracted_lines)

    def _classify_elements(self, elements):
        """Classify elements using document metrics context"""
        classified = []

        for elem in elements:
            # Gather classification signals
            signals = {
                'style': self._analyze_style_signals(elem),
                'position': self._analyze_position_signals(elem),
                'content': self._analyze_content_signals(elem),
                'context': self._analyze_context_signals(elem),
                'metrics': {
                    'relative_size': elem['style']['relative_size'],
                    'relative_spacing': elem['style'].get('relative_spacing', 1.0),
                    'relative_indent': elem['style'].get('relative_indent', 0)
                }
            }

            # Determine content type using all signals
            content_type = self._determine_content_type(signals)

            classified.append({
                'text': elem['text'],
                'type': content_type,
                'style': elem['style'],
                'metrics': signals['metrics']
            })

        return classified

    def _calculate_baseline_metrics(self, font_sizes, line_heights,
                                    paragraph_spacings, margin_lefts, margin_rights):
        """Calculate baseline metrics from collected measurements"""
        baseline = {
            'font_size': None,
            'line_height': None,
            'paragraph_spacing': None,
            'margins': {
                'left': None,
                'right': None
            }
        }

        # Calculate baseline font size (mode of sizes)
        if font_sizes:
            # Round to nearest 0.5 to handle minor variations
            rounded_sizes = [round(size * 2) / 2 for size in font_sizes]
            baseline['font_size'] = statistics.mode(rounded_sizes)

        # Calculate typical line height
        if line_heights:
            # Use median to handle outliers
            baseline['line_height'] = statistics.median(line_heights)

        # Calculate typical paragraph spacing
        if paragraph_spacings:
            # Use median to handle outliers
            baseline['paragraph_spacing'] = statistics.median(paragraph_spacings)

        # Calculate margins
        if margin_lefts:
            # Use mode for margins to find most common alignment
            baseline['margins']['left'] = statistics.mode(
                [round(m * 2) / 2 for m in margin_lefts]
            )
        if margin_rights:
            baseline['margins']['right'] = statistics.mode(
                [round(m * 2) / 2 for m in margin_rights]
            )

        return baseline
