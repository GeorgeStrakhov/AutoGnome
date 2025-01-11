GNOME_HAPPY = r"""
    ,*-~"`^"~-*,
   /  ^^  ^^  ,  \
  |  |⚡| |⚡| |   |
  |  (◕) (◕) |   |
  |   _`~'_  |   |
   \  \___/  /   
    `-.___,-'    
      |_|_|
      |_|_|     
     /\_//\    
    //\_//\\   
   //  |_|  \\  
  //   |_|   \\ 
 //    |_|    \\
//     |_|     \\
"""

GNOME_AFRAID = r"""
    ,*-~"`^"~-*,
   /  ,,  ,,  ,  \
  |  |⚡| |⚡| |   |
  |  (⊙) (⊙) |   |
  |   _`~'_  |   |
   \  /---\  /   
    `-.___,-'    
      |_|_|
      |_|_|     
     /\_//\    
    //\_//\\   
   //  |_|  \\  
  //   |_|   \\ 
 //    |_|    \\
//     |_|     \\
"""

def get_gnome_art(state: str = "normal") -> str:
    """Get the gnome ASCII art based on emotional state"""
    if state == "afraid":
        return GNOME_AFRAID
    return GNOME_HAPPY  # Default to happy/normal state 