# Synthetic fixture contract

`synthetic.png` is an independently authored 320x220 RGB screenshot used to test extraction and comparison.

Known construction facts:

- viewport: 320x220;
- light page background: approximately `#f4f7fc`;
- white rounded surface: approximately x=24, y=20, width=272, height=180;
- visible heading: `Welcome back` near x=48, y=44;
- visible label: `Email` near x=48, y=82;
- input surface: approximately x=48, y=105, width=224, height=34;
- action surface: approximately x=48, y=155, width=224, height=32;
- action text: `Sign in`.

Tests use these independent facts to assert broad geometry and text evidence. They do not compare an implementation result with itself or copy detector calculations into expected values.
