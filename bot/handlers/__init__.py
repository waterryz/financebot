from .start import router

def register_handlers(dp):
    dp.include_router(router)
