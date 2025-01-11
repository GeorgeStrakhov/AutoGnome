GNOME = """
    ,*-~"`^"~-*,
   /  ,,  ,,  ,  \\
  |  |=| |=| |   |
  |  (♥) (♥) |   |
  |   _`~'_  |   |
   \  '---'  /   
    `-.___,-'    
      |_|_|
      |_|_|     
     /\\_//\\    
    //\\_//\\\\   
   //  |_|  \\\\  
  //   |_|   \\\\ 
 //    |_|    \\\\
//     |_|     \\\\
"""

def get_gnome_art(state: str = "normal") -> str:
    """Get the gnome ASCII art, potentially modified based on state"""
    # TODO: Add variations based on state (sleeping, excited, etc.)
    return GNOME 