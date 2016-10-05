from collections import defaultdict

### Helper functions

def get_prefixes(entity, min_length=3, max_length=5):
    # computer science => ['comp sci', ...]
    words = entity.split()
    candidates = ['']
    for word in words:
        new_candidates = []
        for c in candidates:
            if len(word) < max_length:  # Keep word
                new_candidates.append(c + ' ' + word)
            else:  # Shorten
                for i in range(min_length, max_length):
                    new_candidates.append(c + ' ' + word[:i])
        candidates = new_candidates
    # c[1:] is done to remove leading " " character in candidates
    return [c[1:] for c in candidates if c[1:] != entity]

def get_acronyms(entity):
    words = entity.split()
    if len(words) < 2:
        return []
    acronyms = [''.join([w[0] for w in words])]
    # In case BU is represented as B U
    acronyms.extend(' '.join([w[0] for w in words]))
    # May also want to include B.U. if periods not removed by preprocessing
    if 'of' in words:
        # handle 'u of p'
        acronym = ''
        for w in words:
            acronym += w[0] if w != 'of' else ' '+w+' '
        acronyms.append(acronym)
        # handle 'upenn'
        acronym = ''
        for w in words[:-1]:
            acronym += w[0] if w != 'of' else ''
        acronym += words[-1][:4]

        # Handle 'U of Pennsylvania'
        for idx, word in enumerate(words):
            prefix = ' '.join(words[:idx])
            suffix = ' '.join(words[(idx+1):])
            letter = word[0]
            word = prefix + ' ' + letter + ' ' + suffix
            acronyms.append(word.strip())

        acronyms.append(acronym)
    return acronyms


alphabet = ['a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z', ' ']
def get_edits(entity):
    # TODO:  Do we want to consider edit distance 2 or greater?
    # Cross product of edits of tokens for misspellings across multiple tokens?
    if len(entity) < 3:
        return []
    edits = []
    for i in range(len(entity) + 1):
        prefix = entity[:i]
        # Insert
        suffix = entity[i:]
        for c in alphabet:
            new_word = prefix + c + suffix
            edits.append(new_word)

        if i == len(entity):
            continue

        # Delete
        suffix = entity[i+1:]
        new_word = prefix + suffix
        edits.append(new_word)

        # Substitute
        suffix = entity[i+1:]
        for c in alphabet:
            if c != entity[i]:
                new_word = prefix + c + suffix
                edits.append(new_word)

        # Transposition - swapping two letters
        for j in range(i+1, len(entity)):
            mid = entity[i+1:j]
            suffix = entity[j+1:]
            new_word = prefix + entity[j] + mid + entity[i] + suffix
            new_word = new_word.strip()
            if new_word != entity:
                edits.append(new_word)
    return edits


def get_morphological_variants(entity):
    # cooking => cook, cooker
    results = []
    for suffix in ['ing']:
        if entity.endswith(suffix):
            base = entity[:-len(suffix)]
            results.append(base)
            # TODO: Change hard-corded variants!
            # Deal with case "hiking" --> "to hike"
            results.append(base + 'e')
            results.append(base + 's')
            results.append(base + 'er')
            results.append(base + 'ers')
    return results

############################################################

class BaseLexicon(object):
    """
    Base lexicon class defining general purpose functions for any lexicon
    """
    def __init__(self, schema, learned_lex):
        self.schema = schema
        # if True, lexicon uses learned system
        self.learned_lex = learned_lex
        self.entities = {}  # Mapping from (canonical) entity to type (assume type is unique)
        self.word_counts = defaultdict(int)  # Counts of words that show up in entities
        self.lexicon = defaultdict(list)  # Mapping from string -> list of (entity, type)
        self.load_entities()
        self.compute_synonyms()
        print 'Created lexicon: %d phrases mapping to %d entities, %f entities per phrase' % (len(self.lexicon), len(self.entities), sum([len(x) for x in self.lexicon.values()])/float(len(self.lexicon)))
        # TODO: the model cannot handle number entities now
        #print 'Ambiguous entities:'
        #for phrase, entities in self.lexicon.items():
        #    if len(entities) > 1:
        #        print phrase, entities


    def load_entities(self):
        for type_, values in self.schema.values.iteritems():
            for value in values:
                self._add_entity(type_, value.lower())

    def _add_entity(self, type, entity):
        # Keep track of number of times words in this entity shows up
        if entity not in self.entities:
            for word in entity.split(' '):
                self.word_counts[word] += 1
        self.entities[entity] = type

    def lookup(self, phrase):
        return self.lexicon.get(phrase, [])


class Lexicon(BaseLexicon):
    '''
    A lexicon maps freeform phrases to canonicalized entity.
    The current lexicon just uses several heuristics to do the matching.
    '''
    def __init__(self, schema, learned_lex):
        super(Lexicon, self).__init__(schema, learned_lex)


    def compute_synonyms(self):
        # Special cases
        for entity, type in self.entities.items():
            phrases = [entity]  # Representations of the canonical entity
            # Consider any word in the entity that's unique
            # Example: entity = 'university of california', 'university' would not be unique, but 'california' would be
            if ' ' in entity:
                for word in entity.split(' '):
                    if len(word) >= 3 and self.word_counts[word] == 1:
                        phrases.append(word)
            # Consider removing stop words
            mod_entity = entity
            for s in [' of ', ' - ', '-']:
                mod_entity = mod_entity.replace(s, ' ')
            if entity != mod_entity:
                phrases.append(mod_entity)

            synonyms = []
            # Special case -- is there a way to get other rules to handle this?
            if entity == 'facebook':
                synonyms.append('fb')

            # General
            for phrase in phrases:
                synonyms.append(phrase)
                if type != 'person':
                    synonyms.extend(get_edits(phrase))
                    synonyms.extend(get_morphological_variants(phrase))
                    synonyms.extend(get_prefixes(phrase))
                    synonyms.extend(get_acronyms(phrase))

            # Add to lexicon
            for synonym in set(synonyms):
                self.lexicon[synonym].append((entity, type))

    def add_numbers(self):
        numbers = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten']
        for i, n in enumerate(numbers):
            for phrase in [str(i), n]:
                self.lexicon[phrase].append((str(i), 'number'))


    def entitylink(self, raw_tokens):
        '''
        Add detected entities to each token
        Example: ['i', 'work', 'at', 'apple'] => ['i', 'work', 'at', ('apple', 'company')]
        '''
        i = 0
        entities = []
        while i < len(raw_tokens):
            # Find longest phrase (if any) that matches an entity
            for l in range(5, 0, -1):
                phrase = ' '.join(raw_tokens[i:i+l])
                results = self.lookup(phrase)
                if len(results) > 0:
                    entity = None
                    if self.learned_lex:
                        # Will later use learned system -- returns full candidate set for now
                        entity = results
                    else:
                        # NOTE: if more than one match, use the first one.
                        # TODO: disambiguate
                        # prioritize exact match (e.g. hiking, biking)
                        for result in results:
                            if result[0] == phrase:
                                entity = result
                                break
                        if not entity:
                            entity = results[0]
                    entities.append((phrase, entity))
                    i += l
                    break
            if not results:
                entities.append(raw_tokens[i])
                i += 1
        return entities

    def test(self):
        phrases = ['i', 'physics', 'comp sci', 'econ', 'penn', 'cs', 'upenn', 'u penn', 'u of p', 'ucb', 'berekely', 'jessica']
        phrases = ['foodie', 'evening', 'evenings', 'food']
        for x in phrases:
            print x, '=>', self.lookup(x)
        sentence = ['i', 'like', 'hiking', 'biking']
        print self.entitylink(sentence)


class SingleTokenLexicon(BaseLexicon):
    """
    Lexicon that computes per token of entity transforms rather than per phrase transforms
    """
    def __init__(self, schema, learned_lex):
        super(SingleTokenLexicon, self).__init__(schema, learned_lex)


    def compute_synonyms(self):
        # TODO: Add entity-level acronyms?
        # Keep track of tokens we have seen to handle repeats
        seen_tokens = set()
        for entity, type in self.entities.items():
            phrases = []
            mod_entity = entity
            # Consider removing stop words
            for s in [' of ', ' - ', '-']:
                mod_entity = mod_entity.replace(s, ' ')

            # Add all tokens in entity -- we only compute token-level edits (except for acronyms...)
            # Can later optimize away and ensure we don't add same token twice
            entity_tokens = mod_entity.split(' ')
            phrases.extend([t for t in entity_tokens if t not in seen_tokens])
            seen_tokens.update(entity_tokens)

            synonyms = []
            # Special case -- is there a way to get other rules to handle this?
            if entity == 'facebook':
                synonyms.append('fb')

            # General
            for phrase in phrases:
                synonyms.append(phrase)
                if type != 'person':
                    synonyms.extend(get_edits(phrase))
                    synonyms.extend(get_morphological_variants(phrase))
                    synonyms.extend(get_prefixes(phrase))
                    synonyms.extend(get_acronyms(phrase))

            # Add to lexicon
            for synonym in set(synonyms):
                self.lexicon[synonym].append((entity, type))


    def entitylink(self, raw_tokens):
        '''
        Add detected entities to each token
        Example: ['i', 'work', 'at', 'apple'] => ['i', 'work', 'at', ('apple', 'company')]
        Note: Linking works differently here because we are considering intersection of lists across
        token spans so that "univ of penn" will lookup in our lexicon table for "univ" and "penn"
        (disregarding stop words and special tokens) and find their intersection
        '''
        i = 0
        entities = []
        stop_words = set(['of'])
        while i < len(raw_tokens):
            candidate_entities = None
            # Find longest phrase (if any) that matches an entity
            for l in range(5, 0, -1):
                phrase = ' '.join(raw_tokens[i:i+l])
                raw = raw_tokens[i:i+l]
                # Will store candidate entities

                for idx, token in enumerate(raw):
                    results = self.lookup(token)
                    if idx == 0: candidate_entities = results
                    if token not in stop_words:
                        candidate_entities = list(set(candidate_entities).intersection(set(results)))

                # Found some match
                if len(candidate_entities) > 0:
                    entity = None
                    if self.learned_lex:
                        # Will later use learned system -- returns full candidate set for now
                        entity = candidate_entities
                    else:
                        # NOTE: if more than one match, use the first one.
                        # TODO: disambiguate
                        # prioritize exact match (e.g. hiking, biking)
                        for candidate in candidate_entities:
                            if candidate == phrase:
                                entity = candidate
                                break
                        if not entity:
                            entity = candidate_entities
                    entities.append((phrase, entity))
                    i += l
                    break
            if not candidate_entities:
                entities.append(raw_tokens[i])
                i += 1
        return entities


    def test(self):
        phrases = ['foodie', 'evening', 'evenings', 'food']
        for x in phrases:
            print x, '=>', self.lookup(x)

        # NOTE: this is a weird case even though 'biking' is not an entity
        sentence = ['i', 'like', 'hiking', 'biking']
        print self.entitylink(sentence)

        sentence3 = "I went to University of Pensylvania and most my friends are from there".split(" ")
        sentence3 = [t.lower() for t in sentence3]
        print self.entitylink(sentence3)


if __name__ == "__main__":
    from schema import Schema
    # TODO: Update path to location of desired schema used for basic testing
    path = None
    schema = Schema(path)
    lex = SingleTokenLexicon(schema, learned_lex=True)
    lex.test()


