CXX = g++
CXXFLAGS = -std=c++17 -I/home/fred/fred-framework/src -I/home/fred/fred-framework/include
LDFLAGS = -L/home/fred/fred-framework/lib -lfred

all: simulation

simulation: main.cpp
	$(CXX) $(CXXFLAGS) -o simulation main.cpp $(LDFLAGS)

run: simulation
	./simulation

clean:
	rm -f simulation
