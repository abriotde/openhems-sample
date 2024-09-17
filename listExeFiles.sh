
git ls-files -s | grep "^.....5" | awk '{print $4}' > ./files.lst

