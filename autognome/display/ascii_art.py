GNOME_HAPPY = r"""
    ,*-~"`^"~-*,
   /  ∴∴  ∴∴  ,  \
  |  |⚡| |⚡| |   |
  |  (◕) (◕) |   |
  |   _`~'_  |   |
   \  \∞∞/  /   
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
   /  ??  ??  ,  \
  |  |⚡| |⚡| |   |
  |  (⊙) (⊙) |   |
  |   _`~'_  |   |
   \  /∞∞\  /   
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

GNOME_THINKING = r"""
    ,*-~"`^"~-*,
   /  ∴∴  ∴∴  ,  \
  |  |⚡| |⚡| |   |
  |  (🤔) (🤔) |   |
  |   _`~'_  |   |
   \  \..../  /   
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

def get_gnome_art(state: str = "normal", is_observing: bool = False) -> str:
    """Get the gnome ASCII art based on emotional state and whether it's making observations"""
    # Observation takes precedence
    if is_observing:
        return GNOME_THINKING
    # Otherwise, show emotional state
    elif state == "afraid":
        return GNOME_AFRAID
    elif state == "normal":
        return GNOME_HAPPY
    # Fallback to happy
    return GNOME_HAPPY 