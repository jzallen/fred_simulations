CXX = g++
CXXFLAGS = -std=c++17 -Ifred-framework/src -Ifred-framework/include -DLINUX -DFREDVERBOSE -DFREDSTATUS -DFREDWARNING -DFREDDEBUG -DNCPU=1 -m64 -O3
FRED_SRC = fred-framework/src
# Note: Excluding Fred.o since it contains main() function
FRED_OBJECTS = $(FRED_SRC)/Global.o $(FRED_SRC)/Age_Map.o $(FRED_SRC)/Utils.o $(FRED_SRC)/Date.o \
			   $(FRED_SRC)/Events.o $(FRED_SRC)/Random.o $(FRED_SRC)/State_Space.o $(FRED_SRC)/Parser.o \
			   $(FRED_SRC)/Factor.o $(FRED_SRC)/Expression.o $(FRED_SRC)/Predicate.o $(FRED_SRC)/Clause.o \
			   $(FRED_SRC)/Rule.o $(FRED_SRC)/Geo.o $(FRED_SRC)/Abstract_Grid.o $(FRED_SRC)/Abstract_Patch.o \
			   $(FRED_SRC)/Admin_Division.o $(FRED_SRC)/State.o $(FRED_SRC)/County.o $(FRED_SRC)/Census_Tract.o \
			   $(FRED_SRC)/Block_Group.o $(FRED_SRC)/Neighborhood_Layer.o $(FRED_SRC)/Neighborhood_Patch.o \
			   $(FRED_SRC)/Regional_Layer.o $(FRED_SRC)/Regional_Patch.o $(FRED_SRC)/Visualization_Layer.o \
			   $(FRED_SRC)/Visualization_Patch.o $(FRED_SRC)/Person.o $(FRED_SRC)/Demographics.o \
			   $(FRED_SRC)/Link.o $(FRED_SRC)/Travel.o $(FRED_SRC)/Preference.o $(FRED_SRC)/Condition.o \
			   $(FRED_SRC)/Epidemic.o $(FRED_SRC)/Natural_History.o $(FRED_SRC)/Transmission.o \
			   $(FRED_SRC)/Environmental_Transmission.o $(FRED_SRC)/Network_Transmission.o \
			   $(FRED_SRC)/Proximity_Transmission.o $(FRED_SRC)/Group_Type.o $(FRED_SRC)/Place_Type.o \
			   $(FRED_SRC)/Network_Type.o $(FRED_SRC)/Group.o $(FRED_SRC)/Place.o $(FRED_SRC)/Network.o \
			   $(FRED_SRC)/Household.o $(FRED_SRC)/Hospital.o
LDFLAGS = -pthread -ldl

all: simulation

# Build the C++ simulation (keeping for reference)
simulation: main.cpp $(FRED_OBJECTS)
	$(CXX) $(CXXFLAGS) -o simulation main.cpp $(FRED_OBJECTS) $(LDFLAGS)

# Run the C++ simulation
run: simulation
	./simulation

# Run FRED via CLI (recommended approach)
run-fred:
	./run_fred_simulation.sh

# Build FRED framework if needed
build-fred:
	cd fred-framework/src && make

clean:
	rm -f simulation *.o
	rm -rf output/
	rm -f simulation_config.fred
