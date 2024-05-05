import random
import string

generated_strings = set()

def generate_unique_string(length=10):
    while True:
        random_string = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        if random_string not in generated_strings:
            generated_strings.add(random_string)
            return random_string