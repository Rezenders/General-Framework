import numpy as np
import pandas as pd
from evaluation_template import evaluation_template 

class Brier_minFDE_joint(evaluation_template):
    r'''
    The value :math:`F` of the Brier minimum Final Displacement Error (assuming :math:`N_{agents,i}` jointly predicted agents :math:`j`), is calculated in the following way:
        
    .. math::
        F = {1 \over{N_{samples} }} \sum\limits_{i = 1}^{N_{samples}}
            \left( \left(1 - { P_{KDE,i} \left(\{\{\{x_{pred,i,p_{\min,i},j} (t), y_{pred,i,p_{\min,i},j} (t) \} \, | \; \forall\, t \in T_{O,i}\} \, | \; \forall \, j \} \right)   
            \over{\sum\limits_{p = 1}^{\vert P \vert} P_{KDE,i} \left(\{\{\{x_{pred,i,p,j} (t), y_{pred,i,p,j} (t) \} \, | \; \forall\, t \in T_{O,i}\} \, | \; \forall \, j \} \right)}}\right) ^ 2
            \sqrt{{1\over{N_{agents,i}}} \sum\limits_{j = 1}^{N_{agents,i}} 
            \left( x_{i,j}(\max T_{O,i}) - x_{pred,i,p_{\min,i},j} (\max T_{O,i}) \right)^2 + \left( y_{i,j}(\max T_{O,i}) - y_{pred,i,p_{\min,i},j} (\max T_{O,i}) \right)^2} \right)
        
    Here, :math:`p_{\min,i}` is the prediction with the lowest FDE, with

    .. math::
        p_{\min,i} = \underset{p \in P}{arg \min} \sqrt{{1\over{N_{agents,i}}} \sum\limits_{j = 1}^{N_{agents,i}} 
            \left( x_{i,j}(\max T_{O,i}) - x_{pred,i,p,j} (\max T_{O,i}) \right)^2 + \left( y_{i,j}(\max T_{O,i}) - y_{pred,i,p,j} (\max T_{O,i}) \right)^2} \right)
            
    and :math:`P_{KDE,i}` is a sample and agent specific gaussian Kernel Density Estimate trained on all predictions (:math:`p \in P`)
    for sample :math:`i \in \{1, ..., N_{samples}\}` and agent :math:`j`
    
    .. math::
        \{\{\{x_{pred,i,p,j} (t), y_{pred,i,p,j} (t) \} \, | \; \forall\, t \in T_{O,i}\} \, | \; \forall \, j \}

    Here, :math:`P` are the set of predictions made for a specific sample :math:`i \in \{1, ..., N_{samples}\}`
    at the predicted timesteps :math:`T_{O,i}`. :math:`x` and :math:`y` are here the actual observed positions, while 
    :math:`x_{pred}` and :math:`y_{pred}` are those predicted by a model.

    Here, the number of predictions :math:`|P|` can be set using the kwargs, under the key 'num_preds'. If not set, None is assumed.
    '''
    def set_default_kwargs(self):
        if 'num_preds' not in self.metric_kwargs:
            self.metric_kwargs['num_preds'] = None
            
        if 'include_pov' not in self.metric_kwargs:
            self.metric_kwargs['include_pov'] = True

    def setup_method(self):
        self.set_default_kwargs()
     
    def evaluate_prediction_method(self):
        # Get ground truth and predicted paths
        Path_true, Path_pred, Pred_steps = self.get_true_and_predicted_paths(self.metric_kwargs['num_preds'])

        # Get the log likelihoods of the pred samples according to the pred samples
        _, KDE_log_prob_pred = self.get_KDE_probabilities(joint_agents = True)

        # Get the probabilities
        P = np.exp(KDE_log_prob_pred[...,0])

        # Scale P to get sum(p) = 1 over axis 1
        P = P / P.sum(1, keepdims = True) # shape (N_samples, N_preds)

        # Get the number of samples and agents
        Pred_agents = Pred_steps.any(-1)
        Num_steps = Pred_steps.sum(-1).max(-1)
        Num_agents = Pred_agents.sum(-1)
        
        # Get squared distance
        Diff = ((Path_true - Path_pred) ** 2).sum(-1)
        
        # Get mean over agents
        Diff = Diff.sum(2) / Num_agents[:,np.newaxis,np.newaxis]
        
        # Get absolute distance
        Diff = np.sqrt(Diff)
        
        # Take last timestep
        Diff = Diff[np.arange(len(Diff)),:,Num_steps - 1] # shape (N_samples, N_preds)
        
        # Get argmin over predictions
        pred_idx = np.argmin(Diff, axis = 1)

        # Min over predictions
        sample_idx = np.arange(Diff.shape[0])

        Diff = Diff[sample_idx, pred_idx]
        P = P[sample_idx, pred_idx]

        # Get brier diff
        Diff = Diff + (1 - P) ** 2
        
        # Mean over samples and agents
        Error = Diff.mean()
        
        return [Error]
    
    def partial_calculation(self = None):
        options = ['No', 'Sample', 'Pred_agents']
        return options[2]  
    
    def get_output_type(self = None):
        self.set_default_kwargs()
        if self.metric_kwargs['include_pov']:
            return 'path_all_wi_pov'
        else:
            return 'path_all_wo_pov'
    
    def get_opt_goal(self = None):
        return 'minimize'
    
    def get_name(self = None):
        self.set_default_kwargs()
        if self.metric_kwargs['num_preds'] == None:
            N_p = ''
            N_f = ''
            N_l = ''
        else:
            N_p = str(self.metric_kwargs['num_preds']) + ' samples, '
            N_f = str(self.metric_kwargs['num_preds'])
            N_l = str(self.metric_kwargs['num_preds']) + ', '
        
        if self.metric_kwargs['include_pov']:
            P_p = ''
            P_f = ''
            P_l = ''
        else:
            P_p = ', exclude POV'
            P_f = 'nP'
            P_l = 'nP, '

        names = {'print': 'Brier min FDE (' + N_p + 'joint prediction' + P_p + ')',
                'file': 'Brier minFDE' + N_f + '_joint' + P_f,
                'latex': r'\emph{Brier min FDE$_{' + N_l + P_l + r'joint}$ [m]}'}
        return names
    
    
    def check_applicability(self):
        return None
    
    
    def is_log_scale(self = None):
        return True
    
    
    def requires_preprocessing(self):
        return False
    
    def allows_plot(self):
        return False
    
    def metric_boundaries(self = None):
        return [0.0, None]
