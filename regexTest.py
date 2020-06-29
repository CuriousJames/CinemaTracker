# coding=utf8
# the above tag defines encoding for this document and is for Python 2.x compatibility

import re

regex = r"^([\s\S]*Cinema:\s)"
regex2 = r"\n([\s\S]*)"

test_str = ("\n"
            "Dear My Name,\n\n"
            "Thank you for your booking online and we hope you enjoy \"d awesome: Film\".\n\n"
            "Your online booking has been successful and your tickets have been booked\n"
            "at:\n\n"
            "Cinema: Some Place\n"
            "To see: d awesome: Film\n"
            "On: 6/7/20 19:4 PM\n\n"
            "Auditorium:\n"
            "Screen 1\n\n"
            "Tickets*:\n"
            "Adult (Limitless): EFBFBD.")

subst = ""

# You can manually specify the number of replacements by changing the 4th argument
result = re.sub(regex,  subst, test_str, 1)
result = re.sub(regex2, subst, result, 1)

if result:
    print("-->" + result + "<--")

# Note: for Python 2.7 compatibility, use ur"" to prefix the regex and u"" to prefix the test string and substitution.
