"""
Created on 12 April 2011
@author: jog
"""
from __future__ import division
from gevent import monkey; monkey.patch_all()
from bottle import *                #@UnusedWildImport
from ProcessingModule import *      #@UnusedWildImport
from InstallationModule import *    #@UnusedWildImport
from UpdateManager import *
from DatawareDB import *            #@UnusedWildImport
from EnergyDB import *           #@UnusedWildImport
import time                         #@Reimport
import OpenIDManager
import logging.handlers
import math
import json
from functools import wraps
import datetime
import urllib2
import urllib
from gevent.event import Event
from gevent.queue import JoinableQueue
import gevent
import signal
#//////////////////////////////////////////////////////////
# SETUP LOGGING FOR THIS MODULE
#//////////////////////////////////////////////////////////


pqueue = JoinableQueue()
pid = str(os.getpid())
print "pid is %s" % pid

log = logging.getLogger( "console_log" )
dlog = logging.getLogger( "dlog" )

class std_writer( object ):
    def __init__( self, msg ):
        self.msg = msg
    
    def write(self, data):
        data = data.replace( '\n', '' ) \
                   .replace( '\t', '' )
        if len( data ) > 0 :
            log.error( self.msg + ": " + data )

@route( '/triggertest', method="GET")
def triggertest():
    user = check_login()
    if user:
        um.trigger({    
                                    "type": "test",
                                    "message": "a new execution has been undertaken!",
                                    "data": json.dumps({"a":"thing"})                       
                                })
        return json.dumps({"result":"success"})
    return json.dumps({"result":"error"})

@route( '/executiontest', method="GET")
def triggertest():
    user = check_login()
    executions = datadb.fetch_executions()    
    execution = executions[0]
    
    if user:
        um.trigger({  "type":"execution",
                    "message":"test message %d" % um.queuelen(),
                    "data": json.dumps(executions[0])
        
                                         
        })
        #'result': executions[0]['result'],
        #'parameters': executions[0]['parameters']
                                       
        return json.dumps({"result":"success"})
    return json.dumps({"result":"error"})
        
  
    
@route( '/stream', method = "GET", )
def stream():
    try:
        user = check_login()
        if ( not user ): 
            yield json.dumps({"success":"false"})
            
    except Exception, e:
         yield json.dumps({"success":"false"})
         
    try:
        um.event.wait()
        message = um.latest()
       
        #if (message['user'] and message['user'] == user['user_id']):
        log.info("sending %s" % message['message'])
        jsonmsg = json.dumps(message)
        yield jsonmsg
        
    except Exception, e:  
        log.error("longpoll exception")

#//////////////////////////////////////////////////////////
# DATAWARE WEB-API CALLS
#//////////////////////////////////////////////////////////


def format_success( url, ):
   
    return json.dumps({
        'success':True, 
        'redirect':url,  
    })
        

#///////////////////////////////////////////////


def format_failure( cause, error, ):
   
    return json.dumps({ 
        'success':False, 
        'cause':cause,        
        'error':error,  
    })
        

#///////////////////////////////////////////////
  

    
@route( '/schema', method = "GET", )
def schema():
    subdomain = request.urlparts.netloc.split('.')[0]
    schema = resourcedb.fetch_schema(subdomain)
    return json.dumps({"schema":schema})
    
@route( '/install', method = "GET", )
def install():
    
    resource_name = request.GET.get( "resource_name", None )
    
    try:
        user = check_login()
        if ( not user ): redirect( ROOT_PAGE )
    except RegisterException, e:
        redirect( "/register" )
    except LoginException, e:
        return error( e.msg )
    except Exception, e:
        return error( e )        
        
    return template( 'install_page_template', user=user, resource_name=resource_name, catalog_uri=CATALOG_URI) 
    

#///////////////////////////////////////////////
 
 
@route( '/install_request', method = "GET" )
def install_request():
    
    try:
        user = check_login()
        if ( not user ): redirect( ROOT_PAGE )
    except RegisterException, e:
        redirect( "/register" )
    except LoginException, e:
        return error( e.msg )
    except Exception, e:
        return error( e )        

    catalog_uri = request.GET.get( "catalog_uri", None )
    resource_name = request.GET.get( "resource_name", None )
    
    try: 
        url = im.initiate_install( user[ "user_id" ], catalog_uri, resource_name, RESOURCE_URI, REALM)
        return format_success( url )
    except ParameterException, e:
        return format_failure( "resource", e.msg )
    except CatalogException, e:    
        return format_failure( "catalog", e.msg )
        
         
#///////////////////////////////////////////////


@route( '/install_complete', method = "GET" )
def install_complete():
    
    try:
        user = check_login()
    except RegisterException, e:
        redirect( "/register" )
    except LoginException, e:
        return error( e.msg )
    except Exception, e:
        return error( e )  
    
    error = request.GET.get( "error", None )
    state = request.GET.get( "state", None )
    code = request.GET.get( "code", None )
        
    if ( error ):
        try:
            im.fail_install( user, state )
            #TODO: tell the user that the installation failed (a redirect?)
            return "installation failed: %s" % \
                ( request.GET.get( "error_description", "unspecified error" ) )
                
        except ParameterException, e:
            return e.msg

    else:
        #complete the install, swapping the authorization code
        #we've received from the catalog, for the access_token
        try:
            im.complete_install( user, state, code )
            
        except ParameterException, e:
            #TODO: make this more explanatory
            return e.msg
        
        except CatalogException, e:
            #TODO: make this more explanatory
            return e.msg
        
        except Exception, e:
            return  e
        
        #TODO: tell the user that the installation succeeded (a redirect?)
        redirect( "/" )
        #return "installation success"


@route( '/view_executions')
def view_executions():   
   
    try:
        user = check_login()
        if ( not user ): redirect( ROOT_PAGE )
    except RegisterException, e:
        redirect( "/register" )
    except LoginException, e:
        return error( e.msg )
    except Exception, e:
        return error( e ) 
   
    executions = datadb.fetch_executions()    
    return template('executions_template',  user=user, executions=json.dumps(executions)) 
    
@route( '/test_query', method = ["GET", "POST"])
def test_query():
  
    try:
        user = check_login()
        if ( not user ): redirect( ROOT_PAGE )
    except RegisterException, e:
        redirect( "/register" )
    except LoginException, e:
        return error( e.msg )
    except Exception, e:
        return error( e ) 
    
    if request.method=="GET":
        try:
            
            query = request.GET['query']
            data = pm.invoke_test_processor_sql(query)
	    result = json.loads( 
                data.replace( '\r\n','\n' ), 
                strict=False 
            )
            
            if result['success']:
                values = json.loads(result['return']) 
                if isinstance(values, list):
                    if len(values) > 0:
                        if isinstance(values[0], dict):
                            keys = list(values[0].keys())
                            return template('result_template', user=user, result=values, keys=keys)
                return data
            else:
                return json.dumps({"result": "Error running sql"}) 
                
        except Exception, e:
   		return json.dumps({"result": "Error running sql"}) 

    if request.method=="POST":
        try:
            jsonParams =  request.forms.get('parameters')
            query = request.forms.get('query')
            data = pm.test_processor(user, query, jsonParams)
            
            result = json.loads( 
                data.replace( '\r\n','\n' ), 
                strict=False 
            )
            
            log.info(result)
            
            if result['success']:
                values = result['return']
                if isinstance(values, list):
                    if len(values) > 0:
                        if isinstance(values[0], dict):
                            keys = list(values[0].keys())
                            return template('result_template', result=values, keys=keys)
            return data
            
    
        except Exception, e:
            raise e   
            
            
@route( "/static/:filename" )
def user_get_static_file( filename ):
    
    return static_file( filename, root='%s/static/' % ROOT_PATH )



@route( "/static/:path#.+#" )

def user_get_static_file( path ):
   
    return static_file( path, root='%s/static/' % ROOT_PATH )



#//////////////////////////////////////////////////////////
# 3RD PARTY PROCESSOR SPECIFIC WEB-API CALLS
#//////////////////////////////////////////////////////////
   
    
@route( '/invoke_processor', method = "POST")
def invoke_processor():
    
    try:
        
        access_token = request.forms.get( 'access_token' )
        
        jsonParams = request.forms.get( 'parameters' )
        
        result_url = request.forms.get( 'result_url' )
        
        view_url = request.forms.get( 'view_url' )
        
        #added to queue to handle asynchronously
        print "adding the request to the queue!"
        
        pqueue.put({'access_token':access_token, 
                    'jsonParams':jsonParams, 
                    'result_url':result_url,
                    'view_url':view_url
                    })
        
        print "returning success"
        return json.dumps({"result":"success"})
       
    except Exception, e:
        raise e
        return json.dumps({ 
            'success':False,        
            'error':e  
        })            

#///////////////////////////////////////////////
 
 
@route( '/permit_processor', method = "POST" )
def permit_processor():

    #we receive a resource_token and resource_id that matches us,
    #proving that the message is from the catalog, along with 
    #details of the query the client is proposing...
    try:
        install_token = request.forms.get( 'install_token' )
        client_id = request.forms.get( 'client_id' )
        resource_name = request.forms.get( 'resource_name' )
        query = request.forms.get( 'query' ).replace( '\r\n','\n' )
        expiry_time = request.forms.get( 'expiry_time' )        

        result = pm.permit_processor( 
            install_token,
            client_id,
            resource_name,
            query,
            expiry_time 
        )
        
        #the result, if successful, will include an processing_token
        return result
    
    except Exception, e:
        raise e
          

#///////////////////////////////////////////////
 
 
@route( '/revoke_processor', method = "POST" )
def revoke_processor( user_name = None ):
    log.info("revoking processor! %s" % user_name);
    try:
        install_token = request.forms.get( 'install_token' )
        access_token = request.forms.get( 'access_token' )
        
        
        result = pm.revoke_processor( 
            install_token=install_token,
            access_token=access_token,
        )
        
        return result
    
    except Exception, e:
        raise e


    
#//////////////////////////////////////////////////////////
# OPENID SPECIFIC WEB-API CALLS
#//////////////////////////////////////////////////////////


@route( '/login', method = "GET" )
def openID_login():
    
    try: 
        username = request.GET[ 'username' ]    
    except: 
        username = None
     
    try:      
        provider = request.GET[ 'provider' ]
    except: 
        return template( 'login_page_template', user=None )
    
    try:
        url = OpenIDManager.process(
            realm=REALM,
            return_to=REALM + "/checkauth",
            provider=provider,
            username=username
        )
    except Exception, e:
        return error( e )
    
    #Here we do a javascript redirect. A 302 redirect won't work
    #if the calling page is within a frame (due to the requirements
    #of some openid providers who forbid frame embedding), and the 
    #template engine does some odd url encoding that causes problems.
    return "<script>self.parent.location = '%s'</script>" % (url,)
    

#///////////////////////////////////////////////

 
@route( "/checkauth", method = "GET" )
def authenticate():
    
    o = OpenIDManager.Response( request.GET )
    
    #check to see if the user logged in succesfully
    if ( o.is_success() ):
        
        user_id = o.get_user_id()
         
        #if so check we received a viable claimed_id
        if user_id:
            
            try:
                
                user = datadb.fetch_user_by_id( user_id )
              
                #if this is a new user add them
                if ( not user ):
                    datadb.insert_user( o.get_user_id() )
                    datadb.commit()
                    user_name = None
                else :
                    user_name = user[ "user_name" ]
                
                set_authentication_cookie( user_id, user_name  )
                
            except Exception, e:
                return error( e )
            
            
        #if they don't something has gone horribly wrong, so mop up
        else:
            delete_authentication_cookie()

    #else make sure the user is still logged out
    else:
        delete_authentication_cookie()
        
    return "<script>self.parent.location = '%s'</script>" % ( REALM + ROOT_PAGE,)
       
       
#///////////////////////////////////////////////


@route( "/login_local", method = "GET" )
def login_local():
    
    user_name = request.GET.get( "user_name", None )   
    try:
        user = datadb.fetch_user_by_name( user_name )
        set_authentication_cookie( user[ "user_id" ], user_name  )
                
    except Exception, e:
        return error( e )
        
    return "<script>self.parent.location = '%s'</script>" % ( REALM + ROOT_PAGE,)
       
       
#///////////////////////////////////////////////


@route('/logout')
def logout():
    
    delete_authentication_cookie()
    redirect( ROOT_PAGE )
    
        
#///////////////////////////////////////////////
 
         
def delete_authentication_cookie():
    
    response.delete_cookie( 
        key=EXTENSION_COOKIE,
    )
            
#///////////////////////////////////////////////


def set_authentication_cookie( user_id, user_name = None ):
    
    #if the user has no "user_name" it means that they
    #haven't registered an account yet    
    if ( not user_name ):
        json = '{"user_id":"%s","user_name":null}' \
            % ( user_id, )
        
    else:
        json = '{"user_id":"%s","user_name":"%s"}' \
            % ( user_id, user_name )
         
    response.set_cookie( EXTENSION_COOKIE, json )
                            

#//////////////////////////////////////////////////////////
# RESOURCE SPECIFIC WEB-API CALLS
#//////////////////////////////////////////////////////////


class LoginException ( Exception ):
    
    def __init__(self, msg):
        self.msg = msg


#///////////////////////////////////////////////  


class RegisterException ( Exception ):
    """Base class for RegisterException in this module."""
    
    pass

    
#///////////////////////////////////////////////


def valid_email( str ):
    
    return re.search( "^[A-Za-z0-9%._+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,4}$", str )


#///////////////////////////////////////////////


def valid_name( str ):

    return re.search( "^[A-Za-z0-9 ']{3,64}$", str )


#///////////////////////////////////////////////
    
@route( '/register', method = "GET" )
def user_register():
    
    try:
       
        user_id = extract_user_id()
       
    except LoginException, e:
        return error( e.msg )
    except Exception, e:
        return error( e )
    
    errors = {}
    
    #if the user has submitted registration info, parse it
    try: 
        request.GET[ "submission" ]
        submission = True;
    except:
        submission = False
        
    if ( submission ): 
        #validate the user_name supplied by the user
        try:
            user_name = request.GET[ "user_name" ]
            if ( not valid_name( user_name ) ):
                errors[ 'user_name' ] = "Must be 3-64 legal characters"
            else: 
                match = datadb.fetch_user_by_name( user_name ) 
                if ( not match is None ):
                    errors[ 'user_name' ] = "That name has already been taken"                    
        except:
            errors[ 'user_name' ] = "You must supply a valid user name"
    
        #validate the email address supplied by the user
        try:
            email = request.GET[ "email" ]
            if ( not valid_email( email ) ):
                errors[ 'email' ] = "The supplied email address is invalid"
            else: 
                match = datadb.fetch_user_by_email( email ) 
                if ( not match is None ):
                    errors[ 'email' ] = "That email has already been taken"
        except:
            errors[ 'email' ] = "You must supply a valid email"


        #if everything is okay so far, add the data to the database    
        if ( len( errors ) == 0 ):
            try:
               
                match = datadb.insert_registration( user_id, user_name, email) 
                datadb.commit()
                
                #also insert the list of this user's resources (provided in the config file..)
		for resource in RESOURCES:
                    datadb.insert_resource( user_id, resource)
                datadb.commit()
                 
            except Exception, e:
                return error( e )

            #update the cookie with the new details
            set_authentication_cookie( user_id, user_name )
            
            #return the user to the home page
            redirect( ROOT_PAGE )

    #if this is the first visit to the page, or there are errors    
    else:
        email = ""
        user_name = ""
        
    return template( 
        'register_page_template', 
        user=None, 
        email=email,
        user_name=user_name,
        errors=errors ) 
    

#///////////////////////////////////////////////


def error( e ):
    
    return  "An error has occurred: %s" % ( e )

      
#///////////////////////////////////////////////  
    
    
def extract_user_id():
    
    cookie = request.get_cookie( EXTENSION_COOKIE )
        
    #is the user logged in? First check we have a cookie...
    if cookie:
        #and that it contains suitably formatted data
        try:
            data = json.loads( cookie )
        except:
            delete_authentication_cookie()
            raise LoginException( "Your login data is corrupted. Resetting." )
        
        #and then that it contains a valid user_id
        try:
            user_id =  data[ "user_id" ]
            return user_id
        except:
            delete_authentication_cookie()
            raise LoginException( "You are logged in but have no user_id. Resetting." )
    else:
        None

  
#///////////////////////////////////////////////  
    
    
def check_login():

    #first try and extract the user_id from the cookie. 
    #n.b. this can generate LoginExceptions
    user_id =extract_user_id()
    
    if ( user_id ) :
        
        #we should have a record of this id, from when it was authenticated
        user = datadb.fetch_user_by_id( user_id )
        
        if ( not user ):
            delete_authentication_cookie()
            raise LoginException( "We have no record of the id supplied. Resetting." )
        
        #and finally lets check to see if the user has registered their details
        if ( user[ "user_name" ] is None ):
            raise RegisterException()
        
        return user
        
    #if the user has made it this far, their page can be processed accordingly
    else:
        return None   
    

@route( '/liveupdate', method = "GET" )
def liveupdate( ):
    try:
        user = check_login()
    except RegisterException, e:
        redirect( "/register" ) 
    except LoginException, e:
        return error( e.msg )
     
    return template('live_update_template', user=user);
#///////////////////////////////////////////////  
    
    
@route( '/', method = "GET" )     
@route( '/home', method = "GET" )
def home( ):  
   
    try:
        user = check_login()
    except RegisterException, e:
        redirect( "/register" ) 
    except LoginException, e:
        return error( e.msg )
      
    if user is None:
        redirect( "/login" ) 
    
    installs = datadb.fetch_catalog_installs(user['user_id'])
    resources = datadb.fetch_user_resources(user['user_id'])
    summary = resourcedb.fetch_summary()
    return template( 'home_page_template', user=user, resources=json.dumps(resources), installs=installs, data=json.dumps(summary),  template_name="energy_data");
 
@route('/summary')
def summary():
    try:
        user = check_login()
    except RegisterException, e:
        redirect( "/register" ) 
    except LoginException, e:
        return error( e.msg )
      
    if user is None:
        redirect( "/login" ) 
    
    frm = None
    to = None 
    
    if request.params.get('from') is not None:
        frm = request.params.get('from') 
    
    if request.params.get('to') is not None:
        to = request.params.get('to')     
    
    if frm is not None:
        frm=datetime.datetime.fromtimestamp(int(frm)).strftime("%Y/%m/%d:%H:%M:%S")
        print "GOT FROM %s" % frm
    if to is not None:
        to=datetime.datetime.fromtimestamp(int(to)).strftime("%Y/%m/%d:%H:%M:%S")
        print "GOT TO %s" % to
        
    data = resourcedb.fetch_summary(frm=frm, to=to)
    #print "FROM IS %s" % datetime.datetime.fromtimestamp(int(frm)).strftime("%Y/%m/%d:%H:%M:%S")
    #data = resourcedb.fetch_summary() 
    #else:   
    #data = resourcedb.fetch_summary()    
        
    return json.dumps(data)
    
@route('/generate_fake_data')
def generatedata():
    
    try:
        user = check_login()
    except RegisterException, e:
        redirect( "/register" ) 
    except LoginException, e:
        return error( e.msg )
      
    if user is None:
        redirect( "/login" ) 
    
    #generate 5 days worth of data
    resourcedb.generate_fake_data(60*24*5)    
    redirect( ROOT_PAGE )

@route('/generate_fake_data_forever')
def generatedata():
    
    try:
        user = check_login()
    except RegisterException, e:
        redirect( "/register" ) 
    except LoginException, e:
        return error( e.msg )
      
    if user is None:
        redirect( "/login" )
         
    gevent.spawn(fakegenerator)  
    redirect( ROOT_PAGE )        
    
#return a list of all resources (id, name, installed) for this user 
@route('/resources')
def resources():   
    try:
        user = check_login()
    except RegisterException, e:
        redirect( "/register" ) 
    except LoginException, e:
        return error( e.msg )
      
    if user is None:
        redirect( "/login" ) 

    return json.dumps(datadb.fetch_user_resources(user['user_id']))
   
#///////////////////////////////////////////////  
    
@route('/purge')
def purge():
    datadb.purgedata()
    redirect( ROOT_PAGE )

def fakegenerator():
    while True:
        print "creating fake data"
        resourcedb.generate_fake_data(1)    
        gevent.sleep(3)
            
def worker():
    while True:
        request = pqueue.get() 
        try:            
           
            result = pm.invoke_processor_sql( 
                request['access_token'], 
                request['jsonParams'],
                request['view_url']
            )
           
            if not(result is None):
                url = request['result_url']
                data = urllib.urlencode(json.loads(result))
                req = urllib2.Request(url,data)
                f = urllib2.urlopen(req)
                response = f.read()
                f.close()
        
        except Exception, e:   
            log.error("Exception! - error returning results")
            log.error(e) 
        finally:
            pqueue.task_done()
            
#//////////////////////////////////////////////////////////
# MAIN FUNCTION
#//////////////////////////////////////////////////////////

def main():
    
 
   
    global datadb, resourcedb
    global um,pm,im  
    #-------------------------------
    # setup logging
    #-------------------------------
    log.setLevel( logging.DEBUG )
    dlog.setLevel( logging.DEBUG )    

    # create handlers
    #LOCAL
    ch = logging.StreamHandler(sys.stdout)
    
    fh = logging.handlers.TimedRotatingFileHandler( 
        filename='/var/log/dataware/dataware_resource_data.log',
        when='midnight', 
        interval=21 )
        
    # create formatter and add it to the handlers
    formatter = logging.Formatter( '--- %(asctime)s [%(levelname)s] %(message)s' )
    ch.setFormatter( formatter )
    fh.setFormatter( formatter )    

    # add the handlers to the logger
    log.addHandler( ch )
    dlog.addHandler( fh )    
            
    # redirect standard outputs to prevent errors running the process
    # as a daemon (due to print statements in python socket libraries.
    sys.stdout = std_writer( "stdout" )
    sys.stderr = std_writer( "stderr" )
    
    
    #-------------------------------
    # declare initialization in logs
    #-------------------------------        
    print "-"*40
    print "DATAWARE IGNITION"
    print "PORT = %s" % PORT
    print "HOST = %s" % HOST
    print "REALM = %s" % REALM
    print "BOTTLE_QUIET = %s" % BOTTLE_QUIET
    print "-"*40
    
    #---------------------------------
    # Initialization
    #---------------------------------
    
    try:
       
        resourcedb = EnergyDB(configfile, "ResourceDB")
        resourcedb.connect()
        resourcedb.check_tables()
        
        datadb = DataDB(configfile, "DatawareDB" )
        datadb.connect()
        datadb.check_tables()
    
        log.info( "database initialization completed... [SUCCESS]" );
    except Exception, e:
        log.error( "database initialization error: %s" % ( e, ) )
        exit()
         
    #---------------------------------
    # module initialization
    #---------------------------------
    try:    
       
        #the update manager maintains a queue of messages to be sent to connected clients.
         
        um = UpdateManager()
        pm = ProcessingModule( datadb, resourcedb, um )
        im = InstallationModule( RESOURCE_NAME, RESOURCE_URI, datadb )
        gevent.signal(signal.SIGQUIT, gevent.shutdown) 
        gevent.spawn(worker)
        pqueue.join()
       
        log.info( "module initialization completed... [SUCCESS]" );
    except Exception, e:
        log.error( "module initialization error: %s" % ( e, ) )
      
    #---------------------------------
    # Web Server initialization
    #---------------------------------
    try:
        debug( True )
        run( host=HOST, port=PORT, server='gevent')
    except Exception, e:  
        log.error( "Web Server Exception: %s" % ( e, ) )
        exit()
   
    #---------------------------------
    # Initialization Complete
    #---------------------------------
    log.info("-"*40)



#-------------------------------
# constants
#-------------------------------

configfile = sys.argv[1]
Config = ConfigParser.ConfigParser()
Config.read(configfile)

ROOT_PATH = Config.get("DatawareResource", "root_path") 
EXTENSION_COOKIE = "dataware_logged_in"
PORT = Config.get("DatawareResource", "port")
HOST = "0.0.0.0"  
BOTTLE_QUIET = True 
ROOT_PAGE = "/"
RESOURCE_NAME   = Config.get("DatawareResource", "resource_name")

RESOURCES       = json.loads(Config.get("Resources", "resources"))
RESOURCE_URI    = "%s:%s" % (Config.get("DatawareResource", "resource_uri"), PORT) 
REALM           = "%s:%s" % (Config.get("DatawareResource", "realm"), PORT)   
#WEB_PROXY      = "http://aproxy:port"

CATALOG_URI     = Config.get("Catalog", "catalog_uri")
#Setup where bottle serves its template files

TEMPLATE_PATH.insert(0, '%s/views' % ROOT_PATH)  
    
if __name__ == '__main__':
    main()
