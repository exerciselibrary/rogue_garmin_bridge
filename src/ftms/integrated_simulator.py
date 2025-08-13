#!/usr/bin/env python3
"""
Integrated FTMS Simulator with Realistic Data and Error Injection

This module integrates the enhanced bike/rower simulators with the
configurable workout scenarios and error injection system.
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Callable
from src.ftms.enhanced_bike_simulator import EnhancedBikeSimulator
from src.ftms.enhanced_rower_simulator import EnhancedRowerSimulator
from src.ftms.workout_scenarios import WorkoutScenarioManager, ErrorType
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('integrated_simulator')


class IntegratedFTMSSimulator:
    """
    Integrated FTMS simulator that combines realistic data generation
    with configurable error injection scenarios.
    """
    
    def __init__(self, device_type: str = "bike", scenario_name: str = "bike_basic"):
        """
        Initialize the integrated simulator.
        
        Args:
            device_type: Type of device to simulate ("bike" or "rower")
            scenario_name: Name of the workout scenario to use
        """
        self.device_type = device_type
        self.scenario_name = scenario_name
        self.running = False
        self.workout_active = False
        self.start_time = 0
        self.workout_duration = 0
        
        # Callbacks
        self.data_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self.status_callbacks: List[Callable[[str, Any], None]] = []
        
        # Initialize components
        self.scenario_manager = WorkoutScenarioManager()
        
        # Load the specified scenario
        if not self.scenario_manager.load_scenario(scenario_name):
            logger.warning(f"Failed to load scenario '{scenario_name}', using default")
            self.scenario_manager.load_scenario("bike_basic" if device_type == "bike" else "rower_basic")
        
        # Initialize the appropriate simulator based on scenario
        scenario_info = self.scenario_manager.get_scenario_info(scenario_name)
        if scenario_info:
            actual_device_type = scenario_info['device_type']
            workout_type = scenario_info['workout_type']
        else:
            actual_device_type = device_type
            workout_type = "standard"
        
        if actual_device_type == "bike":
            self.simulator = EnhancedBikeSimulator(workout_profile=workout_type)
        else:
            self.simulator = EnhancedRowerSimulator(workout_profile=workout_type)
        
        self.device_type = actual_device_type  # Update to match scenario
        
        logger.info(f"Integrated simulator initialized: {actual_device_type} with scenario '{scenario_name}'")
    
    def register_data_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register a callback function to receive simulated FTMS data"""
        self.data_callbacks.append(callback)
        logger.debug(f"Registered data callback: {callback.__name__ if hasattr(callback, '__name__') else 'anonymous'}")
    
    def register_status_callback(self, callback: Callable[[str, Any], None]) -> None:
        """Register a callback function to receive status updates"""
        self.status_callbacks.append(callback)
        logger.debug(f"Registered status callback: {callback.__name__ if hasattr(callback, '__name__') else 'anonymous'}")
    
    def start_simulation(self) -> None:
        """Start the integrated simulation"""
        if self.running:
            logger.warning("Simulation already running")
            return
        
        self.running = True
        self.start_time = time.time()
        self.workout_duration = 0
        
        # Notify status
        self._notify_status("connected", {"device_type": self.device_type, "scenario": self.scenario_name})
        
        # Start the simulation task
        self._start_simulation_task()
        
        logger.info(f"Started integrated {self.device_type} simulation with scenario '{self.scenario_name}'")
    
    def stop_simulation(self) -> None:
        """Stop the integrated simulation"""
        if not self.running:
            logger.warning("Simulation not running")
            return
        
        self.running = False
        self.workout_active = False
        
        # Notify status
        self._notify_status("disconnected", {"device_type": self.device_type})
        
        logger.info("Stopped integrated simulation")
    
    def start_workout(self) -> None:
        """Start a workout session"""
        logger.info(f"Starting workout with {self.device_type} simulator and scenario '{self.scenario_name}'")
        
        self.workout_active = True
        self.start_time = time.time()
        self.workout_duration = 0
        
        # Start the underlying simulator
        self.simulator.start_workout()
        
        # Notify status
        self._notify_status("workout_started", {
            "device_type": self.device_type,
            "scenario": self.scenario_name,
            "workout_active": True
        })
    
    def end_workout(self) -> None:
        """End a workout session"""
        logger.info(f"Ending workout with {self.device_type} simulator")
        
        self.workout_active = False
        
        # Get final statistics
        error_stats = self.scenario_manager.get_error_statistics()
        
        # Notify status
        self._notify_status("workout_ended", {
            "device_type": self.device_type,
            "scenario": self.scenario_name,
            "workout_active": False,
            "duration": int(time.time() - self.start_time),
            "error_statistics": error_stats
        })
        
        logger.info(f"Workout ended. Error statistics: {error_stats}")
    
    def _start_simulation_task(self) -> None:
        """Start the simulation task in a proper asyncio context"""
        try:
            # Try to get the current event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # No event loop found, create a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                logger.info("Created new event loop for integrated simulation")
            
            # If the loop is closed, create a new one
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                logger.info("Created new event loop (previous was closed)")
            
            # Clear any existing task
            if hasattr(self, '_simulation_task') and self._simulation_task is not None:
                if not self._simulation_task.done() and not self._simulation_task.cancelled():
                    self._simulation_task.cancel()
                    logger.info("Cancelled existing simulation task")
            
            # Create and start the thread
            import threading
            def run_event_loop():
                logger.info("Starting dedicated integrated simulation thread")
                asyncio.set_event_loop(loop)
                loop.run_forever()
            
            self._loop_thread = threading.Thread(target=run_event_loop, daemon=True)
            self._loop_thread.start()
            logger.info("Started integrated simulation thread")
            
            # Create and store a reference to the task
            self._simulation_task = asyncio.run_coroutine_threadsafe(self._simulation_loop(), loop)
            logger.info("Created integrated simulation task")
            
            # Add a callback to handle task completion
            self._simulation_task.add_done_callback(self._on_simulation_task_done)
            
        except Exception as e:
            logger.error(f"Error starting integrated simulation task: {str(e)}", exc_info=True)
    
    def _on_simulation_task_done(self, task):
        """Handle simulation task completion"""
        try:
            task.result()
        except asyncio.CancelledError:
            logger.info("Integrated simulation task was cancelled")
        except Exception as e:
            logger.error(f"Integrated simulation task failed: {str(e)}")
    
    async def _simulation_loop(self) -> None:
        """Main simulation loop that generates data with error injection"""
        try:
            data_generation_count = 0
            logger.info("Integrated simulation loop STARTED")
            
            while self.running:
                try:
                    current_time = time.time()
                    
                    if self.workout_active:
                        self.workout_duration = int(current_time - self.start_time)
                        
                        # Generate base data from the simulator
                        base_data = self.simulator.generate_data_point(self.workout_duration)
                        
                        if base_data is None:
                            logger.debug("Simulator returned no data (workout may be complete)")
                            await asyncio.sleep(1.0)
                            continue
                        
                        data_generation_count += 1
                        
                        # Check for error injection
                        error_config = self.scenario_manager.should_inject_error(self.workout_duration)
                        
                        if error_config:
                            # Apply error to the data
                            modified_data = self.scenario_manager.apply_error_to_data(base_data, error_config)
                            
                            if modified_data is None:
                                # Connection drop - don't send any data
                                logger.warning(f"[{data_generation_count}] Connection drop - no data sent")
                                await asyncio.sleep(1.0)
                                continue
                            else:
                                # Send modified data
                                logger.warning(f"[{data_generation_count}] Sending data with error: {error_config.error_type.value}")
                                self._notify_data(modified_data)
                        else:
                            # Send normal data
                            logger.debug(f"[{data_generation_count}] Sending normal data: "
                                       f"power={base_data.get('instantaneous_power', base_data.get('instantaneous_power', 0))}")
                            self._notify_data(base_data)
                    
                    else:
                        logger.debug("Workout not active, not generating data")
                    
                    # Wait before next iteration
                    await asyncio.sleep(1.0)
                    
                except asyncio.CancelledError:
                    logger.info("Integrated simulation loop cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error in integrated simulation iteration: {str(e)}", exc_info=True)
                    await asyncio.sleep(1)
                    
        except asyncio.CancelledError:
            logger.info("Integrated simulation loop cancelled")
        except Exception as e:
            logger.error(f"Fatal error in integrated simulation loop: {str(e)}", exc_info=True)
        finally:
            self.running = False
            logger.info(f"Integrated simulation loop ended after generating {data_generation_count} data points")
    
    def _notify_data(self, data: Dict[str, Any]) -> bool:
        """Notify all registered data callbacks with new data"""
        try:
            if len(self.data_callbacks) == 0:
                logger.warning("No data callbacks registered!")
                return False
            
            success_count = 0
            for callback in self.data_callbacks:
                try:
                    callback(data)
                    success_count += 1
                except Exception as e:
                    logger.error(f"Error in data callback: {str(e)}")
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Error in _notify_data: {str(e)}")
            return False
    
    def _notify_status(self, status: str, data: Any) -> None:
        """Notify all registered status callbacks with new status"""
        if len(self.status_callbacks) == 0:
            logger.warning("No status callbacks registered!")
        
        for callback in self.status_callbacks:
            try:
                callback(status, data)
            except Exception as e:
                logger.error(f"Error in status callback: {str(e)}")
    
    def get_scenario_info(self) -> Dict[str, Any]:
        """Get information about the current scenario"""
        return self.scenario_manager.get_scenario_info(self.scenario_name)
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error injection statistics"""
        return self.scenario_manager.get_error_statistics()
    
    def get_available_scenarios(self) -> List[str]:
        """Get list of available scenarios"""
        return self.scenario_manager.get_available_scenarios()
    
    def switch_scenario(self, scenario_name: str) -> bool:
        """
        Switch to a different scenario (only when not running a workout).
        
        Args:
            scenario_name: Name of the new scenario
            
        Returns:
            True if scenario was switched successfully
        """
        if self.workout_active:
            logger.error("Cannot switch scenarios during an active workout")
            return False
        
        if not self.scenario_manager.load_scenario(scenario_name):
            logger.error(f"Failed to load scenario '{scenario_name}'")
            return False
        
        self.scenario_name = scenario_name
        
        # Reinitialize simulator if device type changed
        scenario_info = self.scenario_manager.get_scenario_info(scenario_name)
        if scenario_info and scenario_info['device_type'] != self.device_type:
            self.device_type = scenario_info['device_type']
            workout_type = scenario_info['workout_type']
            
            if self.device_type == "bike":
                self.simulator = EnhancedBikeSimulator(workout_profile=workout_type)
            else:
                self.simulator = EnhancedRowerSimulator(workout_profile=workout_type)
            
            logger.info(f"Switched to {self.device_type} simulator for scenario '{scenario_name}'")
        
        return True


def main():
    """Test the integrated simulator"""
    print("Testing Integrated FTMS Simulator")
    print("=" * 50)
    
    # Test with different scenarios
    scenarios_to_test = ["bike_basic", "bike_connection_issues", "rower_basic"]
    
    for scenario in scenarios_to_test:
        print(f"\nTesting scenario: {scenario}")
        
        # Determine device type from scenario
        device_type = "bike" if "bike" in scenario else "rower"
        
        simulator = IntegratedFTMSSimulator(device_type=device_type, scenario_name=scenario)
        
        # Register test callbacks
        def data_callback(data):
            error_info = ""
            if 'error_injected' in data:
                error_info = f" [ERROR: {data['error_injected']}]"
            
            if device_type == "bike":
                print(f"    Data: Power={data.get('instantaneous_power', 0)}W, "
                      f"Cadence={data.get('instantaneous_cadence', 0)}RPM{error_info}")
            else:
                print(f"    Data: Power={data.get('instantaneous_power', 0)}W, "
                      f"StrokeRate={data.get('stroke_rate', 0)}SPM{error_info}")
        
        def status_callback(status, data):
            print(f"    Status: {status}")
        
        simulator.register_data_callback(data_callback)
        simulator.register_status_callback(status_callback)
        
        # Get scenario info
        info = simulator.get_scenario_info()
        print(f"  Device: {info['device_type']}")
        print(f"  Duration: {info['duration_minutes']} minutes")
        print(f"  Error types: {info['error_types']}")
        
        # Simulate a short workout
        simulator.start_simulation()
        simulator.start_workout()
        
        # Let it run for a few seconds
        time.sleep(3)
        
        simulator.end_workout()
        simulator.stop_simulation()
        
        # Get error statistics
        stats = simulator.get_error_statistics()
        print(f"  Error statistics: {stats}")


if __name__ == "__main__":
    main()