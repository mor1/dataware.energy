package uk.ac.nott.cs.txl.energy;

import gnu.io.CommPortIdentifier;
import gnu.io.PortInUseException;
import gnu.io.SerialPort;
import gnu.io.SerialPortEvent;
import gnu.io.SerialPortEventListener;
import gnu.io.UnsupportedCommOperationException;

import java.io.FileNotFoundException;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Enumeration;
import java.util.Scanner;
import java.util.TooManyListenersException;

//import org.hwdb.srpc.*;

import java.util.Date;
import java.text.SimpleDateFormat;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.sql.Statement;

import java.util.Properties;
import java.io.FileInputStream;
 
public class Monitor implements Runnable, SerialPortEventListener{

    static CommPortIdentifier	portId;
	@SuppressWarnings("rawtypes")
	static Enumeration			portList;
	Scanner						inputScanner;
	SerialPort					serialPort;
	Thread						readThread;
    Connection                  connection;
    SimpleDateFormat format      = new SimpleDateFormat("yyyy/MM/dd:HH:mm:ss"); 

	public static void main(String[] args)
	{
		boolean portFound = false;
		String defaultPort = "/dev/tty.usbserial";
		if (args.length == 0)
		{
			System.out.println("using port: " + defaultPort);
		}
		else if (args.length >= 1)
		{
			defaultPort = args[0];
		}
		
		portList = CommPortIdentifier.getPortIdentifiers();
		while (portList.hasMoreElements())
		{
			portId = (CommPortIdentifier)portList.nextElement();
			if (portId.getPortType() == CommPortIdentifier.PORT_SERIAL)
			{
				if (portId.getName().equals(defaultPort))
				{
					System.out.println("Found port: " + defaultPort);
					portFound = true;
					@SuppressWarnings("unused")
					Monitor reader = new Monitor();
				}
			}
		}
		if ( ! portFound)
		{
			System.out.println("port " + defaultPort + " not found.");
		}

	}

	public Monitor()
	{
		try
		{
		    
		    //read in config file
			String url = "", user ="", password="";
			
			Properties configFile = new Properties();
			
			configFile.load(new FileInputStream("../config.properties"));
			try{
			    String hostname = configFile.getProperty("hostname");
			    String db       = configFile.getProperty("database");
			    String port     = configFile.getProperty("port");
			    
			    user     = configFile.getProperty("user");
			    password = configFile.getProperty("password");
	            url = "jdbc:mysql://" + hostname + ":" + port + "/" + db;
	            System.err.println(url);
			}catch(Exception e){
			    e.printStackTrace();
			    System.exit(-1);
			}
			serialPort = (SerialPort)portId.open("SimpleReadApp", 2000);
			inputScanner = new Scanner(serialPort.getInputStream());
			serialPort.addEventListener(this);
			serialPort.notifyOnDataAvailable(true);
			serialPort.setSerialPortParams(57600, SerialPort.DATABITS_8, SerialPort.STOPBITS_1, SerialPort.PARITY_NONE);
			
			try{
			    connection = DriverManager.getConnection(url, user, password);
			}catch(Exception e){
			    e.printStackTrace();
			    System.exit(-1);
			}
		}
		catch (PortInUseException e)
		{
			e.printStackTrace();
		}
		catch (IOException e)
		{
			e.printStackTrace();
		}
		catch (TooManyListenersException e)
		{
			e.printStackTrace();
		}
		catch (UnsupportedCommOperationException e)
		{
			e.printStackTrace();
		}

	}

	public void run()
	{

	}

	public void serialEvent(SerialPortEvent event)
	{
		switch (event.getEventType())
		{

			case SerialPortEvent.BI:

			case SerialPortEvent.OE:

			case SerialPortEvent.FE:

			case SerialPortEvent.PE:

			case SerialPortEvent.CD:

			case SerialPortEvent.CTS:

			case SerialPortEvent.DSR:

			case SerialPortEvent.RI:

			case SerialPortEvent.OUTPUT_BUFFER_EMPTY:
				break;

			case SerialPortEvent.DATA_AVAILABLE:
				
				System.out.println("starting input scanner");
				Statement statement = null;
				
				try{
				    statement = connection.createStatement();
				}
				catch(SQLException e){
				    e.printStackTrace();
				    break;
				}
				
				while (inputScanner.hasNext())
				{

					String parsableLine = inputScanner.next();
					
					System.err.println(parsableLine);
					
					if(parsableLine.contains("hist"))
					{
						// do nothing
						
					}
					else
					{
						if(parsableLine.contains("msg"))
						{
							try
							{
							    
							    String ts = format.format(new Date()); 
								int sensorId = Integer.parseInt(parseSingleElement(parsableLine, "id"));
								double value = Double.parseDouble(parseSingleElement(parsableLine, "watts"));
								
								if (value > 0){
								    
								    String stmt = String.format("insert into energy_data values(\"%s\", '%d', '%f')", ts, sensorId, value);
								    statement.executeUpdate(stmt);  
								}
							}
							catch(SQLException se){
							    se.printStackTrace();
							}
							catch (NumberFormatException n)
							{
								n.printStackTrace();
							}
							catch (Exception e){
							    System.err.println(e.getMessage());
							    e.printStackTrace();
							}
							if (parsableLine.contains("</msg>"))
							{

								
							}
						}
					}
			    } //end of inputScanner.hasNext()
			default:
			    break;
		}//end of switch
	}

	public String parseSingleElement(String m, String t)
	{
		int start = m.indexOf("<" + t + ">") + t.length() + 2;
		int end = m.indexOf("</" + t + ">");
		return (m.substring(start, end));
	}

}