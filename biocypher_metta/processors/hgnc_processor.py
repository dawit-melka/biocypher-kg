"""
HGNC Gene Symbol Processor.

Maintains mappings between:
- Current HGNC gene symbols
- Previous/alias symbols → current symbols (typed, ambiguity-aware)
- Ensembl gene IDs → HGNC symbols

Data source: HGNC (HUGO Gene Nomenclature Committee)
Update strategy: Time-based (every 48 hours)
"""

import re
import requests
import csv
from io import StringIO
from datetime import datetime
from typing import Dict, Any, List, Optional
from biocypher._logger import logger
from .base_mapping_processor import BaseMappingProcessor


# HGNC's custom download joins multi-valued columns with ", "; older exports used "|".
_MULTI_VALUE_SPLIT = re.compile(r'\s*[,|]\s*')

# Sub-mappings added by the typed alias model. A cache missing any of them was
# written by the old processor and is migrated on load.
_TYPED_KEYS = ('previous_to_symbols', 'alias_to_symbols', 'symbol_to_previous', 'symbol_to_alias')


def _split_multi(value: str) -> List[str]:
    return [v for v in _MULTI_VALUE_SPLIT.split(value or '') if v]


class HGNCProcessor(BaseMappingProcessor):
    HGNC_API_URL = (
        "https://www.genenames.org/cgi-bin/download/custom?"
        "col=gd_hgnc_id&col=gd_app_sym&col=gd_app_name&col=gd_prev_sym&col=gd_aliases"
        "&col=gd_pub_eg_id&col=gd_pub_ensembl_id"
        "&status=Approved&hgnc_dbtag=on&order_by=gd_app_sym_sort&format=text&submit=submit"
    )

    def __init__(
        self,
        cache_dir: str = 'aux_files/hsa/hgnc',
        update_interval_hours: Optional[int] = 48  # HGNC needs time-based (no remote metadata)
    ):
        super().__init__(
            name='hgnc',
            cache_dir=cache_dir,
            update_interval_hours=update_interval_hours
        )

    def get_remote_urls(self):
        return [self.HGNC_API_URL]

    def check_update_needed(self) -> bool:
        """
        Keep HGNC cache behavior predictable.

        Honor the configured update interval first (default: 48h), then fall
        back to base checks only after the interval has elapsed.
        """
        if not self.mapping_file.exists() or not self.version_file.exists():
            logger.info(f"{self.name}: Mapping or version file not found. Update needed.")
            return True

        version_info = self._load_version_info()
        if not version_info or "timestamp" not in version_info:
            logger.warning(f"{self.name}: Invalid version file. Update needed.")
            return True

        if self.update_interval:
            last_update = datetime.fromisoformat(version_info["timestamp"])
            time_since_update = datetime.now() - last_update
            if time_since_update <= self.update_interval:
                days = time_since_update.days
                hours = time_since_update.seconds // 3600
                logger.info(
                    f"{self.name}: Using cached mapping (age: {days} days, {hours} hours; "
                    f"refresh window: {self.update_interval.days} days)."
                )
                return False

        return super().check_update_needed()

    def load_or_update(self, force: bool = False) -> Dict[str, Any]:
        super().load_or_update(force=force)
        if self.mapping and not self._is_typed_format():
            self._migrate_legacy_mapping()
        return self.mapping

    def fetch_data(self) -> str:
        logger.info(f"{self.name}: Fetching data from HGNC API...")
        response = requests.get(self.HGNC_API_URL, timeout=30)
        response.raise_for_status()
        return response.text

    def process_data(self, raw_data: str) -> Dict[str, Dict[str, Any]]:
        reader = csv.DictReader(StringIO(raw_data), delimiter='\t')

        logger.info(f"{self.name}: Available columns: {reader.fieldnames}")

        column_mapping = {
            'symbol': ['Approved symbol', 'Symbol'],
            'hgnc_id': ['HGNC ID'],
            'name': ['Approved name'],
            'entrez_id': ['NCBI Gene ID', 'NCBI Gene ID(supplied by NCBI)'],
            'ensembl_id': ['Ensembl gene ID', 'Ensembl ID(supplied by Ensembl)', 'Ensembl ID'],
            'prev_symbol': ['Previous symbols', 'Previous symbol'],
            'alias_symbol': ['Alias symbols', 'Alias symbol']
        }

        actual_columns = {}
        for key, alternatives in column_mapping.items():
            found = next((col for col in alternatives if col in reader.fieldnames), None)
            if found:
                actual_columns[key] = found
                logger.info(f"{self.name}: Found column for {key}: {found}")
            else:
                logger.info(f"{self.name}: Could not find column for {key}")

        def cell(row, key):
            column = actual_columns.get(key)
            return (row.get(column) or '').strip() if column else ''

        current_symbols = {}
        ensembl_to_symbol = {}
        symbol_to_ensembl = {}
        hgnc_id_to_symbol = {}
        hgnc_id_to_ensembl = {}
        symbol_to_hgnc_id = {}
        symbol_to_name = {}
        symbol_to_entrez = {}
        symbol_to_previous = {}
        symbol_to_alias = {}

        for row in reader:
            symbol = row[actual_columns['symbol']]
            ensembl_id = cell(row, 'ensembl_id')
            hgnc_id = cell(row, 'hgnc_id')

            current_symbols[symbol] = symbol

            # Store HGNC ID to symbol mapping (always, even without Ensembl ID)
            if hgnc_id:
                hgnc_id_to_symbol[hgnc_id] = symbol
                symbol_to_hgnc_id[symbol] = hgnc_id

            if ensembl_id:
                base_ensembl = ensembl_id.split('.')[0]

                # Bidirectional Ensembl ↔ Symbol mappings
                ensembl_to_symbol[ensembl_id] = symbol
                ensembl_to_symbol[base_ensembl] = symbol
                symbol_to_ensembl[symbol] = base_ensembl

                # Store direct HGNC ID to Ensembl mapping when both exist
                if hgnc_id:
                    hgnc_id_to_ensembl[hgnc_id] = base_ensembl

            if cell(row, 'name'):
                symbol_to_name[symbol] = cell(row, 'name')
            if cell(row, 'entrez_id'):
                symbol_to_entrez[symbol] = cell(row, 'entrez_id')

            previous = _split_multi(cell(row, 'prev_symbol'))
            aliases = _split_multi(cell(row, 'alias_symbol'))
            if previous:
                symbol_to_previous[symbol] = previous
            if aliases:
                symbol_to_alias[symbol] = aliases

        mapping = {
            'current_symbols': current_symbols,
            'ensembl_to_symbol': ensembl_to_symbol,
            'symbol_to_ensembl': symbol_to_ensembl,
            'hgnc_id_to_symbol': hgnc_id_to_symbol,
            'hgnc_id_to_ensembl': hgnc_id_to_ensembl,
            'symbol_to_hgnc_id': symbol_to_hgnc_id,
            'symbol_to_name': symbol_to_name,
            'symbol_to_entrez': symbol_to_entrez,
            'symbol_to_previous': symbol_to_previous,
            'symbol_to_alias': symbol_to_alias,
        }
        mapping.update(self._build_alias_indexes(symbol_to_previous, symbol_to_alias))
        return mapping

    @staticmethod
    def _build_alias_indexes(symbol_to_previous, symbol_to_alias) -> Dict[str, Dict[str, Any]]:
        """Invert the per-symbol lists, keeping every candidate.

        ``symbol_aliases`` (str -> str) keeps its historical shape but only holds
        unambiguous entries: a unique previous-symbol match wins, otherwise a
        unique alias-symbol match. Strings shared by several genes are left out
        rather than resolved to whichever row happened to come last.
        """
        previous_to_symbols = {}
        alias_to_symbols = {}
        for symbol, values in symbol_to_previous.items():
            for value in values:
                previous_to_symbols.setdefault(value, set()).add(symbol)
        for symbol, values in symbol_to_alias.items():
            for value in values:
                alias_to_symbols.setdefault(value, set()).add(symbol)

        symbol_aliases = {}
        for value in set(previous_to_symbols) | set(alias_to_symbols):
            target = HGNCProcessor._pick_unique(previous_to_symbols.get(value), alias_to_symbols.get(value))
            if target:
                symbol_aliases[value] = target

        return {
            'previous_to_symbols': {k: sorted(v) for k, v in previous_to_symbols.items()},
            'alias_to_symbols': {k: sorted(v) for k, v in alias_to_symbols.items()},
            'symbol_aliases': symbol_aliases,
        }

    @staticmethod
    def _pick_unique(previous_targets, alias_targets) -> Optional[str]:
        if previous_targets:
            return next(iter(previous_targets)) if len(previous_targets) == 1 else None
        if alias_targets and len(alias_targets) == 1:
            return next(iter(alias_targets))
        return None

    def _is_typed_format(self) -> bool:
        return all(key in self.mapping for key in _TYPED_KEYS)

    def _migrate_legacy_mapping(self):
        """Upgrade a cache written before the typed alias model.

        Prefer a fresh download (the old cache cannot tell previous symbols
        from aliases); if that fails, split the joined legacy keys locally and
        treat every entry as an alias symbol.
        """
        logger.info(f"{self.name}: Cached mapping predates typed aliases; refreshing.")
        legacy = self.mapping
        self.update_mapping(force=True)
        if self._is_typed_format():
            return

        logger.warning(f"{self.name}: Refresh failed; rebuilding alias indexes from the legacy cache.")
        symbol_to_alias = {}
        for joined, symbol in legacy.get('symbol_aliases', {}).items():
            for value in _split_multi(joined):
                symbol_to_alias.setdefault(symbol, [])
                if value not in symbol_to_alias[symbol]:
                    symbol_to_alias[symbol].append(value)
        self.mapping = dict(legacy)
        self.mapping['symbol_to_previous'] = {}
        self.mapping['symbol_to_alias'] = symbol_to_alias
        self.mapping.update(self._build_alias_indexes({}, symbol_to_alias))

    def _ensure_loaded(self):
        if not self.mapping:
            self.load_or_update()

    def resolve_symbol(self, identifier: str) -> Optional[str]:
        """Return the approved symbol for ``identifier`` or None.

        Precedence: approved symbol, then a unique previous symbol, then a
        unique alias symbol; the same three tiers are then retried
        case-insensitively (HGNC lists e.g. "p53" as a TP53 alias). Ambiguous
        or unknown strings return None.
        """
        self._ensure_loaded()
        if identifier in self.mapping.get('current_symbols', {}):
            return identifier
        exact = self.mapping.get('symbol_aliases', {}).get(identifier)
        if exact or identifier in self.mapping.get('previous_to_symbols', {}) \
                or identifier in self.mapping.get('alias_to_symbols', {}):
            return exact

        approved, previous, alias = self._casefold_indexes()
        key = identifier.casefold()
        if key in approved:
            return approved[key][0] if len(approved[key]) == 1 else None
        return self._pick_unique(previous.get(key), alias.get(key))

    def _casefold_indexes(self):
        cached = getattr(self, '_casefold_cache', None)
        if cached is not None and cached[0] is self.mapping:
            return cached[1]

        def fold(mapping_items):
            index = {}
            for value, symbols in mapping_items:
                index.setdefault(value.casefold(), set()).update(symbols)
            return {k: sorted(v) for k, v in index.items()}

        approved = fold((s, [s]) for s in self.mapping.get('current_symbols', {}))
        previous = fold(self.mapping.get('previous_to_symbols', {}).items())
        alias = fold(self.mapping.get('alias_to_symbols', {}).items())
        self._casefold_cache = (self.mapping, (approved, previous, alias))
        return approved, previous, alias

    def get_symbol_candidates(self, identifier: str) -> Dict[str, List[str]]:
        """All approved symbols a string could refer to, grouped by match type."""
        self._ensure_loaded()
        return {
            'approved': [identifier] if identifier in self.mapping.get('current_symbols', {}) else [],
            'previous': list(self.mapping.get('previous_to_symbols', {}).get(identifier, [])),
            'alias': list(self.mapping.get('alias_to_symbols', {}).get(identifier, [])),
        }

    def get_symbol_record(self, symbol: str) -> Dict[str, Any]:
        """Typed nomenclature for one approved symbol (used to build gene aliases)."""
        self._ensure_loaded()
        return {
            'symbol': symbol,
            'hgnc_id': self.mapping.get('symbol_to_hgnc_id', {}).get(symbol),
            'name': self.mapping.get('symbol_to_name', {}).get(symbol),
            'entrez_id': self.mapping.get('symbol_to_entrez', {}).get(symbol),
            'previous_symbols': list(self.mapping.get('symbol_to_previous', {}).get(symbol, [])),
            'alias_symbols': list(self.mapping.get('symbol_to_alias', {}).get(symbol, [])),
        }

    def process_identifier(self, identifier: str) -> Dict[str, Any]:
        self._ensure_loaded()

        current_symbols = self.mapping.get('current_symbols', {})
        symbol_aliases = self.mapping.get('symbol_aliases', {})
        ensembl_to_symbol = self.mapping.get('ensembl_to_symbol', {})

        base_identifier = identifier.split('.')[0] if identifier.startswith('ENSG') else identifier

        if base_identifier in current_symbols:
            return {
                'status': 'current',
                'original': identifier,
                'current': base_identifier
            }

        current_symbol = symbol_aliases.get(base_identifier) or self.resolve_symbol(base_identifier)
        if current_symbol:
            return {
                'status': 'updated',
                'original': identifier,
                'current': current_symbol
            }

        if base_identifier in ensembl_to_symbol:
            return {
                'status': 'ensembl_with_symbol',
                'original': identifier,
                'current': ensembl_to_symbol[base_identifier],
                'ensembl_id': base_identifier
            }

        if base_identifier.startswith('ENSG'):
            return {
                'status': 'ensembl_only',
                'original': identifier,
                'current': base_identifier,
                'ensembl_id': base_identifier
            }

        return {
            'status': 'unknown',
            'original': identifier,
            'current': identifier
        }

    def get_current_symbol(self, identifier: str) -> str:
        result = self.process_identifier(identifier)
        return result['current']

    def get_symbol_from_hgnc_id(self, hgnc_id: str) -> str:
        """
        Get gene symbol from HGNC ID.

        Args:
            hgnc_id: HGNC ID (e.g., "HGNC:11998")

        Returns:
            Gene symbol (e.g., "TP53") or None if not found
        """
        self._ensure_loaded()

        hgnc_id_to_symbol = self.mapping.get('hgnc_id_to_symbol', {})
        return hgnc_id_to_symbol.get(hgnc_id)

    def get_ensembl_id(self, identifier: str) -> str:
        """
        Get Ensembl ID for a gene symbol or HGNC ID.

        Symbols resolve through ``resolve_symbol``: an approved symbol first,
        then a unique previous symbol, then a unique alias symbol.

        Args:
            identifier: Gene symbol (e.g., "TP53", "P53") or HGNC ID (e.g., "HGNC:11998")

        Returns:
            Ensembl gene ID (e.g., "ENSG00000141510") or None if not found
        """
        self._ensure_loaded()

        # Check if it's an HGNC ID (format: HGNC:12345)
        if identifier.startswith('HGNC:'):
            # Try direct HGNC ID to Ensembl mapping first
            hgnc_id_to_ensembl = self.mapping.get('hgnc_id_to_ensembl', {})
            if identifier in hgnc_id_to_ensembl:
                return hgnc_id_to_ensembl[identifier]

            # Fallback: HGNC ID -> symbol -> Ensembl ID
            hgnc_id_to_symbol = self.mapping.get('hgnc_id_to_symbol', {})
            symbol = hgnc_id_to_symbol.get(identifier)
            if symbol:
                symbol_to_ensembl = self.mapping.get('symbol_to_ensembl', {})
                return symbol_to_ensembl.get(symbol)

            return None

        symbol = self.resolve_symbol(identifier)
        if symbol is None:
            return None
        return self.mapping.get('symbol_to_ensembl', {}).get(symbol)
