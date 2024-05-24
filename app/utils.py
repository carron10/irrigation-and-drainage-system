import random
import string
from app.models import (
    CropsStatus,
    FieldZone,
    Meta,
    MyModel,
    Notifications,
    Options,
    Role,
    Schedules,
    SoilStatus,
    Statistics,
    History,
    User,
    build_sample_db,
    db,
)

generated_strings = set()

def generate_unique_string(length=10):
    while True:
        random_string = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        if random_string not in generated_strings:
            generated_strings.add(random_string)
            return random_string
        

def add_or_update_option(name,value):
    option = Options.query.get(name)
    if not option:
        option = Options(option_name=name, option_value=value)
        db.session.add(option)
    else:
        option.option_value = value
        db.session.add(option)
    db.session.commit()
    return option.to_dict()
