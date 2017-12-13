import argparse
import copy

from cocoa.core.dataset import read_examples
from cocoa.model.manager import Manager

from core.event import Event
from core.scenario import Scenario
from core.price_tracker import PriceTracker
from model.preprocess import Preprocessor
from model.parser import Parser
from model.dialogue_state import DialogueState
from model.generator import Templates, Generator
from collections import defaultdict

def parse_example(example, lexicon, templates):
    """Parse example and collect templates.
    """
    kbs = example.scenario.kbs
    parsers = [Parser(agent, kbs[agent], lexicon) for agent in (0, 1)]
    states = [DialogueState(agent, kbs[agent]) for agent in (0, 1)]
    # Add init utterance <start>
    parsed_utterances = [states[0].utterance[0], states[1].utterance[1]]
    for event in example.events:
        writing_agent = event.agent  # Speaking agent
        reading_agent = 1 - writing_agent
        #print event.agent

        received_utterance = parsers[reading_agent].parse(event, states[reading_agent])
        if received_utterance:
            sent_utterance = copy.deepcopy(received_utterance)
            if sent_utterance.tokens:
                sent_utterance.template = parsers[writing_agent].extract_template(sent_utterance.tokens, states[writing_agent])

            templates.add_template(sent_utterance, states[writing_agent])
            parsed_utterances.append(received_utterance)
            #print 'sent:', ' '.join(sent_utterance.template)
            #print 'received:', ' '.join(received_utterance.template)

            # Update states
            states[reading_agent].update(writing_agent, received_utterance)
            states[writing_agent].update(writing_agent, sent_utterance)
    return parsed_utterances

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--transcripts', nargs='*', help='JSON transcripts to extract templates')
    parser.add_argument('--price-tracker-model')
    parser.add_argument('--max-examples', default=-1, type=int)
    # parser.add_argument('--templates', help='Path to load templates')
    # parser.add_argument('--templates-output', help='Path to save templates')
    # parser.add_argument('--model', help='Path to load model')
    # parser.add_argument('--model-output', help='Path to save the dialogue manager model')
    args = parser.parse_args()

    price_tracker = PriceTracker(args.price_tracker_model)
    examples = read_examples(args.transcripts, args.max_examples, Scenario)
    parsed_dialogues = []
    templates = Templates()

    counter = 0
    marker = len(examples) / 10.0
    for example in examples:
        counter += 1
        if counter % marker == 0:
            print counter / float(len(examples))
        if Preprocessor.skip_example(example):
            continue
        utterances = parse_example(example, price_tracker, templates)
        parsed_dialogues.append(utterances)

    '''
    #for d in parsed_dialogues[:2]:
    #    for u in d:
    #        print u
    #import sys; sys.exit()

    # Train n-gram model
    sequences = []
    for d in parsed_dialogues:
        sequences.append([u.lf.intent for u in d])
    manager = Manager.from_train(sequences)
    manager.save(args.model_output)

    templates.finalize()
    templates.save(args.templates_output)

    #templates.dump(n=10)

    # TODO: test model and generator
    generator = Generator(templates)
    action = manager.choose_action(None, context=('<start>', '<start>'))
    print action
    print generator.retrieve('<start>', context_tag='<start>', tag=action, category='car', role='seller').template
    '''

    sequences = defaultdict(int)
    for d in parsed_dialogues:
        for u in d:
            sequences[u.lf.intent] += 1

    total = sum(sequences.values())
    for k, v in sequences.items():
        ratio = 100 * (float(v) / total)
        print("{0} intent occured {1} times which is {2:.2f}%".format(k, v, ratio) )
