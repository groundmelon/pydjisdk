# pydjisdk


### Brief Introduction ###

Another version of [https://github.com/dji-sdk/Onboard-SDK](DJISDK) using python. 

Compatible with dji-sdk version 3.0

Very simple code, sometimes naive! 

This packages aims to provide a skeleton for full featured dji-sdk application. Currently, there is only four functions implmented as member function in **SDKApplication.py** :

1.  ``` get_api_version() ```

2.  ``` active_api() ```

3.  ``` acquire_control() ```

4.  ``` release_control() ```

It is only for testing basic communication functionality. Developers can add more functions based on it.

### Usage ###

1. Rename config_example.yaml to config.yaml and modify it using your own configuration

2. ```$ python app.py```

3. Test basic functions

4. With default configuration, I suggest bringing up 3 terminal windows for using and testing this package: 
	* Terminal 0 : ```$ python app.py```. 

	* Terminal 1 : ```$ tail -f log/python.log``` for debug information

	* Terminal 2 : ```$ tail -f log/broadcast.log``` for broadcast information from fmu.

### About Output and Log ###

Thanks for python's powerful logging module, by default, your cout will only print info, warning and error. More detailed debug information can be see in log/python.log. Also, all broadcast data from fmu will be printed out in log/broadcast.log. 

You can see **logconfig.yaml** for details. Also, you can modify it to meet your demand.

### Code Structure and Explanation ###

**app.py**: A sample for how to use package **pydjisdk**

**SDKApplication.py**: Entrance of all functionalities. Developer can modify / inherit this class to construct a more useful application.

**SerialPort.py**: Provided interfaces related to serial port.

**Sessions.py**: Implementation of Session and Session Manager. When sdk application ask something to fmu and reply is need, session based communication is used. This module maintains sessions, all callbacks when fmu replies or retry when there is no response from fmu.

**EncryptCodec.py**: Use package Crypto to deal with CRC and AES.

**Protocal.py** : Provide message packing and unpacking interfaces according to **dji sdk open protocal**. This package deals with header, command set and command id.

**DataCodec\\*.py**: Provide some codec/decode function according to **dji sdk open protocal**. This package deals with data field in the messages.

**utils.py** : Some helper function.

### CANNOT-FIND-SUITABLE-TITLE-FOR-THIS-PART ###

The reason for there being only four functions is that, it takes too much time for writing encode/decode functions according to official protocal document. And I'm too lazy to do that. 

So, contributions are warmly warmly welcomed!
