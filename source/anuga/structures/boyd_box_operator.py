import anuga
import math

class Boyd_box_operator(anuga.Structure_operator):
    """Culvert flow - transfer water from one rectangular box to another.
    Sets up the geometry of problem
    
    This is the base class for culverts. Inherit from this class (and overwrite
    compute_discharge method for specific subclasses)
    
    Input: Two points, pipe_size (either diameter or width, height),
    mannings_rougness,
    """


    def __init__(self,
                 domain,
                 losses,
                 width,
                 height=None,
                 end_points=None,
                 exchange_lines=None,
                 enquiry_points=None,
                 apron=0.1,
                 manning=0.013,
                 enquiry_gap=0.0,
                 use_momentum_jet=True,
                 use_velocity_head=True,
                 description=None,
                 label=None,
                 structure_type='boyd_box',
                 logging=False,
                 verbose=False):
                     
        anuga.Structure_operator.__init__(self,
                                          domain,
                                          end_points,
                                          exchange_lines,
                                          enquiry_points,
                                          width,
                                          height,
                                          apron,
                                          manning,
                                          enquiry_gap,                                                       
                                          description,
                                          label,
                                          structure_type,
                                          logging,
                                          verbose)     
        
        if isinstance(losses, dict):
            self.sum_loss = sum(losses.values())
        elif isinstance(losses, list):
            self.sum_loss = sum(losses)
        else:
            self.sum_loss = losses
        
        self.use_momentum_jet = use_momentum_jet
        self.use_velocity_head = use_velocity_head
        
        self.culvert_length = self.get_culvert_length()
        self.culvert_width = self.get_culvert_width()
        self.culvert_height = self.get_culvert_height()

        self.max_velocity = 10.0

        self.inlets = self.get_inlets()


        # Stats
        
        self.discharge = 0.0
        self.velocity = 0.0
        
        self.case = 'N/A'



    def discharge_routine(self):

        local_debug = False

        if self.use_velocity_head:
            self.delta_total_energy = self.inlets[0].get_enquiry_total_energy() - self.inlets[1].get_enquiry_total_energy()
        else:
            self.delta_total_energy = self.inlets[0].get_enquiry_stage() - self.inlets[1].get_enquiry_stage()

        self.inflow  = self.inlets[0]
        self.outflow = self.inlets[1]

        if self.delta_total_energy < 0:
            self.inflow  = self.inlets[1]
            self.outflow = self.inlets[0]
            self.delta_total_energy = -self.delta_total_energy



        if self.inflow.get_enquiry_depth() > 0.01: #this value was 0.01:
            if local_debug:
                anuga.log.critical('Specific E & Deltat Tot E = %s, %s'
                             % (str(self.inflow.get_enquiry_specific_energy()),
                                str(self.delta_total_energy)))
                anuga.log.critical('culvert type = %s' % str(culvert_type))
            # Water has risen above inlet


            msg = 'Specific energy at inlet is negative'
            assert self.inflow.get_enquiry_specific_energy() >= 0.0, msg

            if self.use_velocity_head :
                self.driving_energy = self.inflow.get_enquiry_specific_energy()
            else:
                self.driving_energy = self.inflow.get_enquiry_depth()

            depth = self.culvert_height
            width = self.culvert_width
            flow_width = self.culvert_width
            # intially assume the culvert flow is controlled by the inlet
            # check unsubmerged and submerged condition and use Min Q
            # but ensure the correct flow area and wetted perimeter are used
            Q_inlet_unsubmerged = 0.544*anuga.g**0.5*width*self.driving_energy**1.50 # Flow based on Inlet Ctrl Inlet Unsubmerged
            Q_inlet_submerged = 0.702*anuga.g**0.5*width*depth**0.89*self.driving_energy**0.61  # Flow based on Inlet Ctrl Inlet Submerged

            # FIXME(Ole): Are these functions really for inlet control?
            if Q_inlet_unsubmerged < Q_inlet_submerged:
                Q = Q_inlet_unsubmerged
                dcrit = (Q**2/anuga.g/width**2)**0.333333
                if dcrit > depth:
                    dcrit = depth
                    flow_area = width*dcrit
                    perimeter= 2.0*(width+dcrit)
                else: # dcrit < depth
                    flow_area = width*dcrit
                    perimeter= 2.0*dcrit+width
                outlet_culvert_depth = dcrit
                self.case = 'Inlet unsubmerged Box Acts as Weir'
            else: # Inlet Submerged but check internal culvert flow depth
                Q = Q_inlet_submerged
                dcrit = (Q**2/anuga.g/width**2)**0.333333
                if dcrit > depth:
                    dcrit = depth
                    flow_area = width*dcrit
                    perimeter= 2.0*(width+dcrit)
                else: # dcrit < depth
                    flow_area = width*dcrit
                    perimeter= 2.0*dcrit+width
                outlet_culvert_depth = dcrit
                self.case = 'Inlet submerged Box Acts as Orifice'

            dcrit = (Q**2/anuga.g/width**2)**0.333333
            # May not need this .... check if same is done above
            outlet_culvert_depth = dcrit
            if outlet_culvert_depth > depth:
                outlet_culvert_depth = depth  # Once again the pipe is flowing full not partfull
                flow_area = width*depth  # Cross sectional area of flow in the culvert
                perimeter = 2*(width+depth)
                self.case = 'Inlet CTRL Outlet unsubmerged PIPE PART FULL'
            else:
                flow_area = width * outlet_culvert_depth
                perimeter = width+2*outlet_culvert_depth
                self.case = 'INLET CTRL Culvert is open channel flow we will for now assume critical depth'
            # Initial Estimate of Flow for Outlet Control using energy slope 
            #( may need to include Culvert Bed Slope Comparison)
            hyd_rad = flow_area/perimeter
            culvert_velocity = math.sqrt(self.delta_total_energy/((self.sum_loss/2/anuga.g)+(self.manning**2*self.culvert_length)/hyd_rad**1.33333))
            Q_outlet_tailwater = flow_area * culvert_velocity
            
            
            if self.delta_total_energy < self.driving_energy:
                # Calculate flows for outlet control

                # Determine the depth at the outlet relative to the depth of flow in the Culvert
                if self.outflow.get_enquiry_depth() > depth:        # The Outlet is Submerged
                    outlet_culvert_depth=depth
                    flow_area=width*depth       # Cross sectional area of flow in the culvert
                    perimeter=2.0*(width+depth)
                    self.case = 'Outlet submerged'
                else:   # Here really should use the Culvert Slope to calculate Actual Culvert Depth & Velocity
                    dcrit = (Q**2/anuga.g/width**2)**0.333333
                    outlet_culvert_depth=dcrit   # For purpose of calculation assume the outlet depth = Critical Depth
                    if outlet_culvert_depth > depth:
                        outlet_culvert_depth=depth
                        flow_area=width*depth
                        perimeter=2.0*(width+depth)
                        self.case = 'Outlet is Flowing Full'
                    else:
                        flow_area=width*outlet_culvert_depth
                        perimeter=(width+2.0*outlet_culvert_depth)
                        self.case = 'Outlet is open channel flow'

                hyd_rad = flow_area/perimeter



                # Final Outlet control velocity using tail water
                culvert_velocity = math.sqrt(self.delta_total_energy/((self.sum_loss/2/anuga.g)+(self.manning**2*self.culvert_length)/hyd_rad**1.33333))
                Q_outlet_tailwater = flow_area * culvert_velocity

                Q = min(Q, Q_outlet_tailwater)
            else:
                
                pass
                #FIXME(Ole): What about inlet control?

            culv_froude=math.sqrt(Q**2*flow_width/(anuga.g*flow_area**3))
            if local_debug:
                anuga.log.critical('FLOW AREA = %s' % str(flow_area))
                anuga.log.critical('PERIMETER = %s' % str(perimeter))
                anuga.log.critical('Q final = %s' % str(Q))
                anuga.log.critical('FROUDE = %s' % str(culv_froude))

            # Determine momentum at the outlet
            barrel_velocity = Q/(flow_area + anuga.velocity_protection/flow_area)

        # END CODE BLOCK for DEPTH  > Required depth for CULVERT Flow

        else: # self.inflow.get_enquiry_depth() < 0.01:
            Q = barrel_velocity = outlet_culvert_depth = 0.0

        # Temporary flow limit
        if barrel_velocity > self.max_velocity:
            barrel_velocity = self.max_velocity
            Q = flow_area * barrel_velocity

        return Q, barrel_velocity, outlet_culvert_depth
        
        
        
