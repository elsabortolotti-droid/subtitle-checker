#!/usr/bin/env python3
"""
subtitle_checker.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tool QA per la verifica di file sottotitoli .srt
Controlla: timecode sovrapposti, righe troppo lunghe,
caratteri speciali non validi, blocchi malformati,
durate anomale, encoding.

Utilizzo:
  python3 subtitle_checker.py video.srt
  python3 subtitle_checker.py /cartella/srt --report report.txt
  python3 subtitle_checker.py video.srt --fix

Nessuna dipendenza esterna richiesta.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import re
import sys
import argparse
from pathlib import Path
from datetime import timedelta

# ── Costanti standard broadcast ───────────────────────────────────────────────
MAX_CHARS_PER_LINE  = 42     # Standard EBU R37
MAX_LINES_PER_BLOCK = 2      # Max righe per blocco sottotitolo
MIN_DURATION_MS     = 500    # Durata minima consigliata (ms)
MAX_DURATION_MS     = 7000   # Durata massima consigliata (ms)
MAX_CPS             = 25     # Caratteri al secondo — standard leggibilità

TIMECODE_RE = re.compile(
    r"(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})"
)

INVALID_CHARS = ['â€™', 'â€œ', 'â€', 'Ã¨', 'Ã ', 'Ã¹', 'Ã²', 'Ã©', '\x00', '\ufffd']


def tc_to_ms(h, m, s, ms):
    return ((int(h) * 3600 + int(m) * 60 + int(s)) * 1000) + int(ms)


def ms_to_tc(ms):
    s, ms_r = divmod(ms, 1000)
    m, s_r  = divmod(s, 60)
    h, m_r  = divmod(m, 60)
    return f"{h:02d}:{m_r:02d}:{s_r:02d},{ms_r:03d}"


def parse_srt(content):
    """Parsa un file SRT e restituisce lista di blocchi."""
    blocks = []
    raw_blocks = re.split(r'\n\s*\n', content.strip())

    for raw in raw_blocks:
        lines = raw.strip().splitlines()
        if not lines:
            continue

        block = {"raw": raw, "index": None, "start": None, "end": None, "text": []}

        # Numero blocco
        if lines[0].strip().isdigit():
            block["index"] = int(lines[0].strip())
            lines = lines[1:]

        # Timecode
        if lines and TIMECODE_RE.match(lines[0].strip()):
            m = TIMECODE_RE.match(lines[0].strip())
            block["start"] = tc_to_ms(*m.groups()[:4])
            block["end"]   = tc_to_ms(*m.groups()[4:])
            lines = lines[1:]

        block["text"] = lines
        blocks.append(block)

    return blocks


def check_srt(path):
    """Esegue tutti i controlli QA su un file SRT."""
    errors   = []
    warnings = []

    # ── Encoding ──────────────────────────────────────────────────────────────
    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            content = path.read_text(encoding="latin-1")
            warnings.append("⚠  Encoding non UTF-8 rilevato (latin-1). Converti in UTF-8.")
        except Exception as e:
            errors.append(f"✗  Impossibile leggere il file: {e}")
            return errors, warnings, []

    # ── Caratteri corrotti ─────────────────────────────────────────────────────
    for ch in INVALID_CHARS:
        if ch in content:
            errors.append(f"✗  Carattere corrotto/non valido nel file: '{ch}'")

    blocks = parse_srt(content)

    if not blocks:
        errors.append("✗  Nessun blocco sottotitolo trovato. File vuoto o malformato.")
        return errors, warnings, blocks

    prev_end = -1

    for i, block in enumerate(blocks):
        n = block["index"] or (i + 1)

        # ── Timecode mancante ──────────────────────────────────────────────────
        if block["start"] is None or block["end"] is None:
            errors.append(f"✗  Blocco #{n}: timecode mancante o malformato.")
            continue

        start, end = block["start"], block["end"]

        # ── Start > End ────────────────────────────────────────────────────────
        if start >= end:
            errors.append(
                f"✗  Blocco #{n}: start ({ms_to_tc(start)}) >= end ({ms_to_tc(end)}) — timecode invertito."
            )

        # ── Sovrapposizione con blocco precedente ──────────────────────────────
        if start < prev_end:
            errors.append(
                f"✗  Blocco #{n}: sovrapposizione con blocco precedente "
                f"({ms_to_tc(start)} < {ms_to_tc(prev_end)})."
            )

        # ── Durata anomala ─────────────────────────────────────────────────────
        duration = end - start
        if duration < MIN_DURATION_MS:
            warnings.append(
                f"⚠  Blocco #{n}: durata troppo breve ({duration}ms < {MIN_DURATION_MS}ms)."
            )
        elif duration > MAX_DURATION_MS:
            warnings.append(
                f"⚠  Blocco #{n}: durata molto lunga ({duration}ms > {MAX_DURATION_MS}ms)."
            )

        # ── Testo ──────────────────────────────────────────────────────────────
        text_lines = block["text"]

        if not text_lines or all(l.strip() == "" for l in text_lines):
            warnings.append(f"⚠  Blocco #{n}: testo vuoto.")

        if len(text_lines) > MAX_LINES_PER_BLOCK:
            warnings.append(
                f"⚠  Blocco #{n}: {len(text_lines)} righe (max consigliato: {MAX_LINES_PER_BLOCK})."
            )

        full_text = " ".join(text_lines)
        char_count = len(re.sub(r'<[^>]+>', '', full_text))  # Rimuove tag HTML

        for j, line in enumerate(text_lines, 1):
            clean = re.sub(r'<[^>]+>', '', line)
            if len(clean) > MAX_CHARS_PER_LINE:
                warnings.append(
                    f"⚠  Blocco #{n} riga {j}: {len(clean)} caratteri (max: {MAX_CHARS_PER_LINE})."
                )

        # ── CPS (caratteri al secondo) ─────────────────────────────────────────
        if duration > 0:
            cps = (char_count / duration) * 1000
            if cps > MAX_CPS:
                warnings.append(
                    f"⚠  Blocco #{n}: velocità lettura {cps:.1f} cps (max: {MAX_CPS}) — testo troppo veloce."
                )

        prev_end = end

    return errors, warnings, blocks


def print_report(path, errors, warnings, blocks, output=None):
    lines = []
    lines.append(f"\n{'━' * 60}")
    lines.append(f"  📋 Subtitle QA Report")
    lines.append(f"  File   : {path.name}")
    lines.append(f"  Blocchi: {len(blocks)}")
    lines.append(f"  Errori : {len(errors)}")
    lines.append(f"  Warning: {len(warnings)}")
    lines.append(f"{'━' * 60}\n")

    if errors:
        lines.append("── ERRORI ───────────────────────────────────────────────")
        for e in errors:
            lines.append(f"  {e}")
        lines.append("")

    if warnings:
        lines.append("── WARNING ──────────────────────────────────────────────")
        for w in warnings:
            lines.append(f"  {w}")
        lines.append("")

    if not errors and not warnings:
        lines.append("  ✅ Nessun problema rilevato. File conforme agli standard.")
        lines.append("")

    lines.append(f"{'━' * 60}")
    result = "\n".join(lines)
    print(result)

    if output:
        Path(output).write_text(result, encoding="utf-8")
        print(f"\n  Report salvato in: {output}")


def main():
    parser = argparse.ArgumentParser(
        description="Subtitle Checker — QA tool per file .srt"
    )
    parser.add_argument("input",    help="File .srt o cartella con file .srt")
    parser.add_argument("--report", metavar="FILE.txt", help="Salva il report in un file")
    args = parser.parse_args()

    input_path = Path(args.input)

    if not input_path.exists():
        print(f"Errore: '{input_path}' non trovato.")
        sys.exit(1)

    if input_path.is_dir():
        srt_files = list(input_path.rglob("*.srt"))
        if not srt_files:
            print("Nessun file .srt trovato nella cartella.")
            sys.exit(0)
        print(f"Trovati {len(srt_files)} file .srt")
        total_errors = 0
        for f in sorted(srt_files):
            errors, warnings, blocks = check_srt(f)
            print_report(f, errors, warnings, blocks, output=None)
            total_errors += len(errors)
        print(f"\nTotale errori su tutti i file: {total_errors}")
    else:
        errors, warnings, blocks = check_srt(input_path)
        print_report(input_path, errors, warnings, blocks, output=args.report)

        sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
