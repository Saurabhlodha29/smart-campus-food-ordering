"""
FastAPI auth dependencies — stub, implemented in Auth module (migration step 2).

Will contain:
  get_current_user(token: str = Depends(oauth2_scheme)) -> User
  require_role(*roles: str) -> Callable[..., User]
  (Rate-limit middleware also lives under security/ — added in step 12)
"""
