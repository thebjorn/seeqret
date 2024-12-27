
class User:
    def __init__(self, username: str, email: str, pubkey: str):
        self.username = username
        self.email = email
        self.pubkey = pubkey

    @property
    def row(self):
        return [self.username, self.email, self.pubkey]

    def __json__(self):
        return dict(
            username=self.username,
            email=self.email,
            pubkey=self.pubkey
        )

    def __str__(self):
        return f'User({self.username}, {self.email}, {self.pubkey})'
