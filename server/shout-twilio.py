from flask import Flask, request, redirect, url_for, g, current_app
import twilio.twiml
import pusher
import urllib
import json
from os import listdir
from os.path import isfile, join

app = Flask(__name__)

pusher.app_id = ''
pusher.key = ''
pusher.secret = ''

app.p = pusher.Pusher()

data = {
    "count": 0 
}

samples = {
}

phones = {
}

@app.route("/service")
def hello_monkey():
    from_number = request.args.get('From', None)
    call_sid = request.args.get('CallSid', None)
    
    caller = "Shouter"
    print "Service: " + str(from_number)
 
    phones[call_sid] = from_number
    samples[call_sid] = "None"

    resp = twilio.twiml.Response()
    # Greet the caller by name
    resp.say("Hello " + caller)
    # Play an mp3
    # resp.play("http://demo.twilio.com/hellomonkey/monkey.mp3")
 
    # Gather digits.
    with resp.gather(numDigits=1, action="/handle-key", method="GET") as g:
        g.say(""" 
                 Press 1 to record your shout.
                 Press any other key to start over.""")
 
    return str(resp)
 
@app.route("/handle-key")
def handle_key():
    """Handle key press from a user."""
 
    digit_pressed = request.args.get('Digits', None)

    print "handle-key. key: " + str(digit_pressed)

    if digit_pressed == "2":
        resp = twilio.twiml.Response()
        # Dial (310) 555-1212 - connect that number to the incoming caller.
        resp.dial("12345678")
        # If the dial fails:
        resp.say("The call failed, or the remote party hung up. Goodbye.")
 
        return str(resp)
 
    elif digit_pressed == "1":
        resp = twilio.twiml.Response()
        resp.say("Record your shout after the tone. You have 3 seconds.")
        resp.record(maxLength="3", action="/handle-recording")
        return str(resp)
 
    # If the caller pressed anything but 1, redirect them to the homepage.
    else:
        return redirect("/service")
 

@app.route("/handle-recording", methods=["GET", "POST"])
def handle_recording():
    """Play back the caller's recording."""
 
    count = increment_count()

    recording_url = request.form.get("RecordingUrl", None)
    call_sid = request.form.get('CallSid', None)

    print "handle-recording. url: " + str( recording_url )

    from_number = phones[call_sid]
    print "from_number: " + str( from_number )
    
    if from_number:
        sample_id = from_number
    else:
        sample_id = call_sid

    filename = sample_id + ".mp3"

    rec_file = "static/" + filename;
    print "rec file: " + str( rec_file )

    if recording_url:
        urllib.urlretrieve( recording_url, rec_file )
        samples[call_sid] = url_for('static', filename=filename)

    resp = twilio.twiml.Response()
    resp.say("Thanks for shouting.")
    # resp.play(recording_url)

    push_to_pusher("twilio", str(from_number), str(sample_id), str(samples[call_sid]) )

    resp.say("Check the app for your shout.")

    resp.say("Goodbye...")

    return str(resp)


def push_to_pusher(room, phone_nr, sample_id, sample_url):
    print "Pushing to room: " + room + ", url: " + sample_url
    app.p[room].trigger( 'twilio_event', { 'id': sample_id, 'url': sample_url, 'phone': phone_nr } )
    return ""

def increment_count():
    data["count"] += 1
    return data["count"]

@app.route("/list", methods=["GET", "POST"])
def handle_list():
    ret = "{ samples: [\n"
    for f in listdir("static"):
        ret = ret + url_for('static', filename=str(f)) + ", "
        
    ret += "}"

    return str(ret)

@app.route('/get/twilio', methods=['GET'])
def get_twilio():
    callback = request.args.get('callback', False)
    json_str = handle_show()

    if callback:
      content = str(callback) + '(' + json_str + ')'
      return current_app.response_class(content, mimetype='application/json')

    return json_str

def read_samples():
    i = 1
    for f in listdir("static"):
        samples[i] = 'static/' + f
        phones[i] = ""
        i += 1

    return ""

@app.route("/show", methods=["GET", "POST"])
def handle_show():
    
    ret = "{ samples: ["
    for k in samples:
        phone = str(phones[k])
        ret += "{ id: '" + str(k) + "', phone: '" + phone + "', url: '" + str( samples[k] ) + "' }, "
    
    ret += "]  }"

    print "show: " + ret

    return str(ret)

if __name__ == "__main__":
    read_samples()
    app.debug = True
    app.run(host="0.0.0.0")
