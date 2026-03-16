import re

def _build_robust_pattern(phrase):
    r"""
    Internal function: Converts a phrase into a regex pattern.
    Handles:
    1. Hidden characters or line breaks inside words (common in PDFs).
    2. Variable spacing (multiple spaces, tabs, newlines).
    3. Special regex characters within the phrase (escaped).
    
    Example: 'בית אדום' becomes 'ב\s*י\s*ת\s+א\s*ד\s*ו\s*ם'
    """
    # Split the phrase into individual words
    words = phrase.split()
    flexible_words = []
    
    for word in words:
        # Insert optional whitespace (\s*) between every single character in the word
        # This handles the 'בי\nת' case we saw in your PDF debug
        flex_word = r'\s*'.join(re.escape(char) for char in word)
        flexible_words.append(flex_word)
    
    # Join words with mandatory whitespace (\s+) between them
    # This ensures we find the phrase even if there are multiple spaces/lines between words
    return re.compile(r'\s+'.join(flexible_words))


def process_and_search(document_id, page_iterator, phrases_to_find, overlap_size=150):
    """
    Scans a document chunk-by-chunk, applies robust regex matching, 
    and handles overlap buffers to ensure no phrases are missed across page breaks.
    
    Args:
        document_id (str): Identifier for logging (usually the filename).
        page_iterator (iterator): Generator yielding text strings from the document.
        phrases_to_find (list): List of strings to search for.
        overlap_size (int): Number of characters to carry over to the next chunk.
        
    Returns:
        dict: A mapping of {phrase: boolean_result}
    """
    # Use a set for pending phrases for O(1) removals and performance
    pending_phrases = set(phrases_to_find)
    overlap_buffer = ""
    
    # Initialize all phrases as False
    results = {phrase: False for phrase in phrases_to_find}
    
    for page_number, current_page_text in enumerate(page_iterator, start=1):
        print(f"\n[DEBUG] Text found on page {page_number}:")
        print(f"'{current_page_text}'")
        # Short-circuit: Stop processing the file if all phrases have been found
        if not pending_phrases:
            # All phrases found, no need to keep reading/OCR-ing the rest of the file
            break
            
        # Combine the end of the previous page (buffer) with the current page text
        text_to_search = overlap_buffer + current_page_text
        found_in_this_page = set()
        
        for phrase in pending_phrases:
            # Build the regex for the current phrase
            pattern = _build_robust_pattern(phrase)
            
            # Check for a match
            if pattern.search(text_to_search):
                results[phrase] = True
                found_in_this_page.add(phrase)
        
        # Remove found phrases from the pending set so we don't search for them again
        pending_phrases -= found_in_this_page
        
        # Update the overlap buffer: take the last X characters of the current page
        # This ensures phrases split between pages (e.g., 'בית' on p.1 and 'אדום' on p.2) are caught
        if len(current_page_text) > overlap_size:
            overlap_buffer = current_page_text[-overlap_size:]
        else:
            overlap_buffer = current_page_text
            
    return results