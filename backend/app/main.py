app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # sab allow karega (mobile fix)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
