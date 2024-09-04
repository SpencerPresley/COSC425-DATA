from striprtf.striprtf import rtf_to_text

with open('assets/citations.rtf', 'r') as file:
    rtf_content = file.read()
    
plain_text = rtf_to_text(rtf_content)

with open('assets/citations.txt', 'w') as file:
    file.write(plain_text)