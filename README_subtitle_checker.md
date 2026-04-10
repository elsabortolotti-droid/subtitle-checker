# 📋 Subtitle Checker

Tool QA per la verifica automatica di file sottotitoli `.srt`. Controlla la conformità agli standard broadcast EBU R37 e segnala errori e warning con riferimento preciso al numero di blocco.

Sviluppato con background in post-produzione TV (Mediaset, Sky Italia, Local Team).

## Controlli eseguiti

| Controllo | Tipo | Standard |
|---|---|---|
| Timecode malformati o mancanti | Errore | — |
| Start >= End (timecode invertito) | Errore | — |
| Sovrapposizione tra blocchi | Errore | — |
| Caratteri corrotti / encoding non UTF-8 | Errore / Warning | UTF-8 |
| Righe troppo lunghe | Warning | EBU R37: max 42 car. |
| Più di 2 righe per blocco | Warning | Standard broadcast |
| Durata troppo breve (< 500ms) | Warning | Best practice |
| Durata troppo lunga (> 7s) | Warning | Best practice |
| Velocità lettura > 25 CPS | Warning | Standard leggibilità |
| Blocco con testo vuoto | Warning | — |

## Utilizzo

```bash
# Nessuna dipendenza — solo Python 3.7+

# Controlla un singolo file
python3 subtitle_checker.py video.srt

# Controlla tutti i .srt in una cartella
python3 subtitle_checker.py /cartella/sottotitoli

# Salva il report su file
python3 subtitle_checker.py video.srt --report report.txt
```

## Esempio output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📋 Subtitle QA Report
  File   : episodio_01.srt
  Blocchi: 847
  Errori : 2
  Warning: 5
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

── ERRORI ───────────────────────────────────────────────────
  ✗  Blocco #143: sovrapposizione con blocco precedente (00:12:34,100 < 00:12:34,800).
  ✗  Blocco #391: timecode mancante o malformato.

── WARNING ──────────────────────────────────────────────────
  ⚠  Blocco #22 riga 1: 48 caratteri (max: 42).
  ⚠  Blocco #67: durata troppo breve (320ms < 500ms).
  ⚠  Blocco #201: velocità lettura 28.3 cps (max: 25) — testo troppo veloce.
```

## Requisiti

- Python 3.7+
- Nessuna dipendenza esterna

## Contesto

Sviluppato a partire dall'esperienza in post-produzione video per Sky Italia, Mediaset (Donnavventura) e Local Team, dove la verifica dei sottotitoli fa parte del flusso QA standard prima della messa in onda.
