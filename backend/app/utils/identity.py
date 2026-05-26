import random

def generate_ghost_name() -> str:
    """
    Generates a unique, temporary ghost name for the room session.
    
    Note on Profile Pictures (PFPs):
    To maximize backend performance and minimize memory usage, we use frontend-side 
    avatar generation powered by the Dicebear Identicon API:
    https://api.dicebear.com/7.x/identicon/svg?seed=<ghost_name>
    This maps each ghost name deterministically to a premium, visual vector avatar 
    directly in the browser without loading server resources.
    """
    adjectives = ["Silent", "Neon", "Cyber", "Void", "Crimson", "Shadow", "Quantum"]
    nouns = ["Panda", "Spectre", "Ronin", "Cipher", "Wraith", "Nomad", "Glitch"]
    number = random.randint(100, 999)
    
    return f"{random.choice(adjectives)}{random.choice(nouns)}_{number}"
