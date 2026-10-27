# Regenerate the README demo from the repo root:  vhs docs/media/demo.tape
# fold -s keeps the long self-check lines inside the 117-column window.
Output docs/media/demo.gif

Require python3
Require javac

Set Shell "bash"
Set Theme "GitHub Dark"
Set FontSize 15
Set Width 1240
Set Height 760
Set Padding 22
Set WindowBar Colorful
Set BorderRadius 10
Set TypingSpeed 35ms

Type "python3 kv-cache-pool/main.py | fold -s -w 116"
Sleep 300ms
Enter
Sleep 6s

Type "clear"
Enter
Sleep 300ms

Type "python3 dynamic-batcher/main.py | fold -s -w 116"
Sleep 300ms
Enter
Sleep 5s

Type "clear"
Enter
Sleep 300ms

Type "python3 run_all.py"
Sleep 300ms
Enter
Wait@60s
Sleep 3.5s
