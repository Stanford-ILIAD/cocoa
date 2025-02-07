'''
Data structures for events, examples, and datasets.
'''

from util import read_json
from event import Event
from kb import KB

class Example(object):
    '''
    An example is a dialogue grounded in a scenario, has a set of events, and has some reward at the end.
    Created by through live conversation, serialized, and then read for training.
    '''
    def __init__(self, scenario, uuid, events, outcome, ex_id, agents, agents_info=None):
        self.scenario = scenario
        self.uuid = uuid
        self.events = events
        self.outcome = outcome
        self.ex_id = ex_id
        self.agents = agents
        self.agents_info = agents_info

    def add_event(self, event):
        self.events.append(event)

    @classmethod
    def from_dict(cls, raw, Scenario, scenario_db=None):
        if 'scenario' in raw:
            scenario = Scenario.from_dict(None, raw['scenario'])
        # Compatible with old data formats (to be removed)
        elif scenario_db:
            print 'WARNING: scenario should be provided in the example'
            scenario = scenario_db.get(raw['scenario_uuid'])
        else:
            raise ValueError('No scenario')
        uuid = raw['scenario_uuid']
        events = [Event.from_dict(e) for e in raw['events']]
        outcome = raw['outcome']
        ex_id = raw['uuid']
        if 'agents' in raw:
            agents = {int(k): v for k, v in raw['agents'].iteritems()}
        else:
            agents = None
        agents_info = raw.get('agents_info', None)
        return Example(scenario, uuid, events, outcome, ex_id, agents, agents_info=agents_info)

    @classmethod
    def test_dict(cls, raw):
        uuid = raw['scenario_uuid']
        events = [Event.from_dict(e) for e in raw['events']]
        outcome = raw['outcome']
        ex_id = raw['uuid']
        if 'agents' in raw:
            agents = {int(k): v for k, v in raw['agents'].iteritems()}
        else:
            agents = None
        agents_info = raw.get('agents_info', None)
        return Example(None, uuid, events, outcome, ex_id, agents, agents_info=agents_info)


    def to_dict(self):
        return {
            'scenario_uuid': self.scenario.uuid,
            'events': [e.to_dict() for e in self.events],
            'outcome': self.outcome,
            'scenario': self.scenario.to_dict(),
            'uuid': self.ex_id,
            'agents': self.agents,
            'agents_info': self.agents_info,
        }

class Dataset(object):
    '''
    A dataset consists of a list of train and test examples.
    '''
    def __init__(self, train_examples, test_examples):
        self.train_examples = train_examples
        self.test_examples = test_examples

class EvalExample(object):
    '''
    Context-response pairs with scores from turkes.
    '''
    def __init__(self, uuid, kb, agent, role, prev_turns, prev_roles, target, candidates, scores):
        self.ex_id = uuid
        self.kb = kb
        self.agent = agent
        self.role = role
        self.prev_turns = prev_turns
        self.prev_roles = prev_roles
        self.target = target
        self.candidates = candidates
        self.scores = scores

    @staticmethod
    def from_dict(schema, raw):
        ex_id = raw['exid']
        kb = KB.from_dict(schema.attributes, raw['kb'])
        agent = raw['agent']
        role = raw['role']
        prev_turns = raw['prev_turns']
        prev_roles = raw['prev_roles']
        target = raw['target']
        candidates = raw['candidates']
        scores = raw['results']
        return EvalExample(ex_id, kb, agent, role, prev_turns, prev_roles, target, candidates, scores)

############################################################

def read_examples(paths, max_examples, Scenario):
    '''
    Read a maximum of |max_examples| examples from |paths|.
    '''
    examples = []
    for path in paths:
        print 'read_examples: %s' % path
        for raw in read_json(path):
            if max_examples >= 0 and len(examples) >= max_examples:
                break
            examples.append(Example.from_dict(raw, Scenario))
    return examples

def read_dataset(args, Scenario):
    """
    Given the paths of the dataset, parse the json files and convert them into python objects
    :param args: command line arguments
    :param Scenario: Reference to the Scenario Class (found in core.scenario)
    :return: A dataset object with with training_examples and test_examples separated
        Each training example contains a list of events, which include both messages sent to each other
        and commands, like offering a price and accepting one. Each example also contains the outcome of the scenario
        which includes the reward and the agreed upon price
    """
    train_examples = read_examples(args.train_examples_paths, args.train_max_examples, Scenario)
    test_examples = read_examples(args.test_examples_paths, args.test_max_examples, Scenario)
    print("We found {0} train examples and {1} test examples".format(len(train_examples), len(test_examples)))
    dataset = Dataset(train_examples, test_examples)
    return dataset

if __name__ == "__main__":
    lines = read_json("fb-negotiation/scr/data/transformed_test.json")
    for idx, raw in enumerate(lines):
        print Example.from_dict(raw)
