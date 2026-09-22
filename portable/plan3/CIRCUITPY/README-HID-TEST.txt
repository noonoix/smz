HID diagnostic based on 41-fixed-pico-bundle

Copy the files in this folder to CIRCUITPY and replace the old files.
This bundle keeps the known-good 41 runtime and changes only desktop_steps.txt.
It sends no keyboard keys and performs two fixed absolute mouse moves:
(200,200), wait 1.5s, then (1600,800).

If the start sound returns but the cursor does not move, the problem is in
Pro Micro HID absolute reporting/mapping. Restore the original 41 bundle after
this test.
