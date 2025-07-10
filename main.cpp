#include <iostream>
#include "Fred.h"

int main(int argc, char* argv[]) {
    Fred::Global::initialize(argc, argv);
    
    std::cout << "Starting FRED Simulation..." << std::endl;

    // Initialize simulation parameters (basic example)
    Fred::Simulation* simulation = new Fred::Simulation();
    simulation->setup();
    
    // Run simulation steps (basic example)
    for (int day = 0; day < 10; day++) {
        simulation->run_day(day);
        std::cout << "Day " << day << " completed." << std::endl;
    }

    simulation->finish();
    delete simulation;

    std::cout << "FRED Simulation Completed." << std::endl;

    return 0;
}
