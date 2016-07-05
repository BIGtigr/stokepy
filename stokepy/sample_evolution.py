from .headers import *
from .helpers import *

class SampleEvolution:

    def __init__(self, markov_chain, samples, steps, rec_class_states, \
                 memory = 10, tolerance = 0.001):
        """
        markov_chain is a MarkovChain object

        memory and tolerance are optional parameters
        """
        self.P                           = markov_chain.P
        self.phi                         = markov_chain.phi
        self.num_of_steps                = steps
        self.memory                      = memory
        self.num_of_states               = markov_chain.phi.shape[0]
        self.num_of_samples              = samples
        self.states_in_recurrent_classes = rec_class_states
        self.tolerance                   = tolerance

        # place to store values returned from simulation
        self.epdf = None
        # average distribution
        self.pi = None
        # absorption proportions for plotting
        self.absorption_proportions = None


        self.absorbed_proportions_by_recurrent_class = None
        self.mean_absorption_time = None

    def plot_absorption(self):
        plot_absorption_helper(self.absorption_proportions, self.tolerance)

    def run(self):
        """
        Evolves the system by simulating many sample paths
        """
        ### -------------- set stage for simulation -------------- ###
        # create empirical probability distribution function
        epdf    = np.zeros([self.memory, self.num_of_states], dtype = float)
        # initialize the epdf by writing the initial distribution matrix to epdf
        epdf[0] = self.phi[:]
        ap = compute_absorbed_proportions(self.phi, self.states_in_recurrent_classes)
        absorption_proportions = [ap]
        # There is a nuance here.  For epdf, we only keep the most self.memory distributions.
        # We really don't need to full prior history, so this help us conserve memory.
        # However we really DO need the full history of absorption_proportions, because
        # we want to plot the full distribution, over ALL time.
        # The problem is that we don't actually know how many steps it will take for complete
        # (or almost complete) absorption. So, we cannot pre-allocate the size of
        # absorption_proportions (in contrast to epdf, where we can pre-allocate).
        # Therefore, we are stuck "growing the array" (as far as I can tell).

        scaled_phi        = np.rint(self.phi * self.num_of_samples).astype(int)
        simulation_ledger = np.zeros([self.memory, self.num_of_samples], dtype = int)

        # initialize simulation ledger by distributing probabilities
        # from the initial distribution matrix to the sample population
        simulation_ledger_index_1 = 0
        for state_index in range(self.num_of_states):
            simulation_ledger_index_2 = simulation_ledger_index_1 + scaled_phi[state_index]
            simulation_ledger[0, simulation_ledger_index_1:simulation_ledger_index_2] = state_index
            simulation_ledger_index_1 = simulation_ledger_index_2
        # shuffle the columns in the first row
        np.random.shuffle(simulation_ledger[0])

        ### -------------- run the simulation -------------- ###
        step = 0
        while (step < self.num_of_steps) or (np.sum(ap) < 1-self.tolerance):
            # "step" here refers to the location with respect to the number of records
            # since we're looping through the same array
            # Because we are not keeping the entire history, we loop repeatedly through the
            # same array, overwriting old states. We move down the rows of simulation_ledger until we hit
            # the bottom. Then we jump back to the top and overwrite existing arrays.
            # The % operator does modular division and accomplishes the necessary looping.
            current_step = step % self.memory
            next_step    = (step + 1) % self.memory
            for sample in range(self.num_of_samples):
                current_state      = simulation_ledger[current_step, sample]
                # choose random number between 0 and 1
                random_probability = np.random.rand()
                # randomly decide which state sample goes to next
                for next_state in range(self.num_of_states):
                    random_probability -= self.P[current_state, next_state]
                    if random_probability < 0:
                        simulation_ledger[next_step, sample] = next_state
                        break
            vector = np.histogram(simulation_ledger[next_step, :], \
                                              normed = True, bins = range(self.num_of_states + 1))[0]
            epdf[next_step, :] = vector
            ap                 = compute_absorbed_proportions(vector, self.states_in_recurrent_classes)
            absorption_proportions.append(ap)
            step += 1

        # right now, the last distribution is not necessarily on the bottom of the epdf matrix;
        # so, the following code rearranges the rows of the matrix to make sure the final distribution is on bottom
        epdf = np.roll(epdf, self.memory - next_step - 1, axis = 0)
        # plot_absorption(absorption_proportions, tolerance = self.tolerance)

        ### -------- set results -------- ###
        self.epdf = epdf
        self.pi   = np.mean(epdf, 0)
        self.absorption_proportions = absorption_proportions
        self.absorbed_proportions_by_recurrent_class = absorption_proportions[-1]

        # get mean absorption time
        absorbed_marginal = get_newly_absorbed_proportions(\
                            self.absorption_proportions, self.tolerance)
        times = np.arange(absorbed_marginal.shape[0])
        self.mean_absorption_time = absorbed_marginal.dot(times)
        return None
