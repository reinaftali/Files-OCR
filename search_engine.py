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


def process_and_search(document_id, page_iterator, search_dict, overlap_size=150):
    """
    Args:
        document_id (str): Identifier for logging.
        page_iterator (iterator): Generator yielding text chunks.
        search_dict (dict): A mapping of {Category_Name: [list_of_phrases]}
        overlap_size (int): Number of characters to carry over.
    Returns:
        dict: A mapping of {Category_Name: boolean_result}
    """
    # The tracking is for the keywords (categories), not the individual words.
    pending_keys = set(search_dict.keys())
    results = {key: False for key in search_dict.keys()}
    overlap_buffer = ""
    
    for page_number, current_page_text in enumerate(page_iterator, start=1):
        if not pending_keys:
            break # All categories found, you can finish the scan
            
        text_to_search = overlap_buffer + current_page_text
        found_in_this_page = set()
        
        for key in pending_keys:
            #Go through all phrases associated with the specific category or word
            for phrase in search_dict[key]:
                pattern = _build_robust_pattern(phrase)
                if pattern.search(text_to_search):
                    results[key] = True
                    found_in_this_page.add(key)
                    break #Once we have found one phrase, the category is checked, moving to the next one.
        
        pending_keys -= found_in_this_page
        
        if len(current_page_text) > overlap_size:
            overlap_buffer = current_page_text[-overlap_size:]
        else:
            overlap_buffer = current_page_text
            
    return results

def check_subject_relevance(text, subject_header, keyword):
    """
    Checks for the dynamic subject header and the target keyword.
    Returns: (subject_found, keyword_found)
    """
    # Build regex for the dynamic header 
    subject_pattern = _build_robust_pattern(subject_header)
    match = subject_pattern.search(text)
    
    if not match:
        return False, False
        
    # Search within a 500-character buffer after the header
    start_idx = match.end()
    search_area = text[start_idx : start_idx + 500]
    
    # Build regex for the required keyword (e.g., "דחוף")
    keyword_pattern = _build_robust_pattern(keyword)
    if keyword_pattern.search(search_area):
        return True, True
        
    return True, False