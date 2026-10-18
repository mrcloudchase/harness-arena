# csvstat

Summarize one numeric column of a CSV file from the command line.

```
python csvstat.py data.csv --col price
count=120 min=0.5 max=99 mean=23.41
```

## Options

- `file`: the CSV file; the first row must be the header.
- `--col NAME` (required): the column to summarize. Cells that are not numbers are skipped.
- `--delim CHAR`: the field delimiter, default `,` (use `--delim ';'` for semicolon files).

## Exit status

`0` on success; `1` if the column has no numeric values; `2` if the column does not exist.
