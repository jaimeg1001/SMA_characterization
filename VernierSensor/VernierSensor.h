#ifndef VernierSensor_h
#define VernierSensor_h
#include "Arduino.h"


class VernierSensor
{
public:
    VernierSensor();
	void begin();
    void autoID();//this is the function for the autoID code
    // it returns calibration information
    int channel()       { return _channel; };
    float voltageID()   { return _voltageID; }; 
    int sensorNumber()  { return _sensorNumber;};  
    char* sensorName()   { return _sensorName ;};
    char* shortName()    { return _shortName  ;};
    char* sensorUnits()  { return _sensorUnits;};
    float slope()        { return _slope; }; 
    float intercept()    { return _intercept; }; 
    float cFactor()      { return _cFactor; }; 
    int calEquationType(){ return _calEquationType; };
    int page()           { return _page; }; 

    float readSensor();//This function converts count to sensor reading
    float sensorReading()     { return _sensorReading; };

protected://  also known as local

    float _voltageID;
    int  _channel;
    int _sensorNumber;
    char _sensorName[16];
    char _shortName[12];// 11 char + terminator
    char _sensorUnits[7];
    float _slope;
    float _sum;
    float _intercept;
    float _cFactor;
    int _calEquationType;
    int _page;
    float _sensorReading;
    float _distance;
    // this misc. variable is used many places
    int _i;
};
#endif

// END OF FILE
