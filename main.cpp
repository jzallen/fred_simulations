#include <iostream>
#include "Global.h"

int main(int argc, char* argv[]) {
    std::cout << "Starting FRED Simulation..." << std::endl;

    // Since FRED is designed as a complete simulation framework with its own main,
    // we'll just demonstrate accessing FRED's Global variables and functions
    
    // Initialize some basic Global properties
    Global::Simulation_Day = 0;
    Global::Simulation_Days = 10;
    
    std::cout << "FRED Global variables accessible:" << std::endl;
    std::cout << "Simulation Day: " << Global::Simulation_Day << std::endl;
    std::cout << "Simulation Days: " << Global::Simulation_Days << std::endl;
    std::cout << "Days per week: " << Global::DAYS_PER_WEEK << std::endl;
    std::cout << "Adult age: " << Global::ADULT_AGE << std::endl;

    // Simulate a simple loop
    for(int day = 0; day < 5; day++) {
        Global::Simulation_Day = day;
        std::cout << "Simulated day " << day << " completed." << std::endl;
    }

    std::cout << "FRED Integration Demo Completed." << std::endl;

    return 0;
}
