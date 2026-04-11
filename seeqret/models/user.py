from ..seeqrypt.nacl_backend import public_key


class User:
    def __init__(self, username: str, email: str, pubkey: str,
                 slack_handle: str | None = None,
                 slack_key_fingerprint: str | None = None,
                 slack_verified_at: int | None = None):
        self.username = username
        self.email = email
        self.pubkey = pubkey
        self.slack_handle = slack_handle
        self.slack_key_fingerprint = slack_key_fingerprint
        self.slack_verified_at = slack_verified_at

    @property
    def public_key(self):
        return public_key(self.pubkey)

    @property
    def row(self):
        return [self.username, self.email, self.pubkey]

    def __json__(self):
        return dict(
            username=self.username,
            email=self.email,
            pubkey=self.pubkey,
            slack_handle=self.slack_handle,
            slack_key_fingerprint=self.slack_key_fingerprint,
            slack_verified_at=self.slack_verified_at,
        )

    def __str__(self):
        return f'User({self.username}, {self.email}, {self.pubkey})'
