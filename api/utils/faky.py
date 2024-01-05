import random
import faker
from faker.providers import BaseProvider
from pytest import Session


class Faky:
    max_units: int
    max_review: int
    fake: faker.Faker

    class TaskProvider(BaseProvider):
        def unit(self, max_val):
            return random.randint(1, max_val)

        def unit_sample(self, max_val: int, sample_size: int):
            return random.sample(range(1, max_val + 1), sample_size)

        def rating(self, max_val):
            return random.randint(1, max_val)

    def __init__(self, max_units):
        self.max_units = max_units
        self.fake = faker.Faker()
        self.fake.add_provider(self.TaskProvider)
        self.max_review = 5

    def unit(self):
        return self.fake.unit(self.max_units)

    def unit_sample(self, sample_size):
        return self.fake.unit_sample(self.max_units, sample_size)

    def rating(self):
        return self.fake.rating(self.max_review)


def create_faky(db: Session):
    from api import models

    unit_count = db.query(models.WorkUnit).count()
    return Faky(unit_count)
