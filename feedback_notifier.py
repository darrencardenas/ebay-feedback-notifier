#!/ur/bin/env python3

# -----------------------------------------------------------------------------
# eBay Feedback Notifier
# -----------------------------------------------------------------------------
# This script sends a notification email if an eBay user's feedback rating 
# changes.
#
# Requirements: 
#   - Create a free SMTP2GO account at smtp2go.com.
#   - Modify the values in the "REQUIRED CUSTOMIZATIONS" section below.
#
# Procedure:
#   - Run the script using Python version 3.0 or higher.
# 
# Usage: feedback_notifier.py [-h] -u USERNAME [-f FILENAME]
#
# -----------------------------------------------------------------------------
import argparse
import os.path
import re
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.request import urlopen

# -----------------------------------------------------------------------------
# REQUIRED CUSTOMIZATIONS
# -----------------------------------------------------------------------------

EMAIL_RECIPIENT = 'recipient@email.com'
EMAIL_SENDER    = 'sender@email.com'

SMTP2GO_USERNAME = 'user@email.com'
SMTP2GO_PASSWORD = 'password'

# -----------------------------------------------------------------------------
# Optional customizations
# -----------------------------------------------------------------------------

DEFAULT_SCORES_FILE = 'scores.txt'

SMTP2GO_SERVER = 'mail.smtp2go.com'
SMTP2GO_PORT   = 2525  # 8025, 587 and 25 can also be used

EMAIL_SUBJECT = 'eBay feedback notification'

EBAY_USR_URL = 'https://www.ebay.com/usr/' 


def get_cmdline_args():
    """Return arguments from the command-line."""
    parser = argparse.ArgumentParser(description='An eBay feedback notifier.')
    parser.add_argument('-u', action='store', required=True, 
                        help='an eBay username', dest='username')
    parser.add_argument('-f', action='store', required=False,
                        help='a text file to write feedback scores ' + \
                        '(default: scores.txt)', dest='filename', 
                        default=DEFAULT_SCORES_FILE)       
    return parser.parse_args().username, parser.parse_args().filename
    
  
def send_smtp2go_email(sender, recipient, subject, body):
    """Send an email through an SMTP server."""
    msg = MIMEMultipart('mixed')
    
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient
    
    text_message = MIMEText(body, 'plain')
    msg.attach(text_message)
    
    mailServer = smtplib.SMTP(SMTP2GO_SERVER, SMTP2GO_PORT) 
    mailServer.ehlo()
    mailServer.starttls()
    mailServer.ehlo()
    mailServer.login(SMTP2GO_USERNAME, SMTP2GO_PASSWORD)
    mailServer.sendmail(sender, recipient, msg.as_string())
    mailServer.close()    
    

class Notifier:
    """Class that send an email if a user's feedback changes."""

    def __init__(self, username, scores_file):
        """Instantiate a Notifier object."""
        
        self.username = username                
        self.profile_url = EBAY_USR_URL + self.username
        
        self.scores_file = scores_file         
        self.old_scores = {'overall': 0, 'positive': 0, 
                           'neutral': 0, 'negative': 0}
        self.new_scores = {'overall': 0, 'positive': 0, 
                           'neutral': 0, 'negative': 0}

        self.errors = []

        self.print_header()        
        self.get_old_scores()        
        self.get_new_scores()                
        self.compare_scores()
        
        
    def compare_scores(self):        
        """Check for score changes and send an email if there are any."""
        # Scores file exists
        if self.old_scores_exist:
        
            # Check for score changes
            if self.new_scores['overall']  != self.old_scores['overall']  or \
               self.new_scores['positive'] != self.old_scores['positive'] or \
               self.new_scores['neutral']  != self.old_scores['neutral']  or \
               self.new_scores['negative'] != self.old_scores['negative']:
               
                print('Feedback changed. Sending email notification ... ', 
                      end=""),
                
                # Build the email body
                email_body = self.username + '\'s feedback changes:\n\n'
                for key in self.new_scores:
                    if self.new_scores[key] != self.old_scores[key]:
                        email_body += key + ': ' + str(self.old_scores[key]) \
                                      + ' -> ' + str(self.new_scores[key]) + \
                                      '\n'

                # Email using SMTP2GO
                send_smtp2go_email(EMAIL_SENDER, EMAIL_RECIPIENT, EMAIL_SUBJECT,
                                   email_body)  
                                   
                print('done.') 
              
            else:
                print('Feedback has not changed.')

    def get_new_scores(self): 
        """Read new feedback scores from a webpage."""
        # Download user profile webpage
        print('\nDownloading new values from: %s\n' %(self.profile_url))
        html_content = urlopen(self.profile_url).read().decode('utf-8')

        # Get the new overall score
        pattern = self.username + "\'s feedback score is (\d+)"
        match = re.search(pattern, html_content, re.IGNORECASE);
        if match == None:
            self.errors.append('overall score not found')
            self.new_scores['overall'] = '0'
        else:  
            # Insert comma separators
            self.new_scores['overall'] = format(int(match.group(1)), ',d')            
            print('new overall score : ' + self.new_scores['overall'])
          
        # Get the new positive, neutral, and negative scores  
        for key in self.new_scores:
            if key != 'overall':
                # Get the new scores          
                pattern = r"title=\"" + key + r"\"><div class=\"score\">" + \
                          "<span class=\"gspr icf[npt]\"></span><span " + \
                          "class=\"num\">([\d\,]+)</span>"
                match = re.search(pattern, html_content, re.IGNORECASE);
                if match == None:
                    self.errors.append(key + ' score not found')
                    self.new_scores[key] = '0'
                else:  
                    self.new_scores[key] = match.group(1)
                    print('new ' + key + ' score: ' + self.new_scores[key]) 
          
        # Handle errors    
        if len(self.errors) == 0:
            print('\nNo errors\n')
        else:
            print('\nErrors: ' + str(self.errors) + '\n')

        # Write new values to file  
        with open(self.scores_file, 'w') as f:
            s = self.time_stamp +  '\n\n' + \
                'overall: ' + str(self.new_scores['overall']) + '\n' + \
                'positive: ' + str(self.new_scores['positive']) + '\n' + \
                'neutral: ' + str(self.new_scores['neutral']) + '\n' + \
                'negative: ' + str(self.new_scores['negative'])
            f.write(s)            
        f.closed

    def get_old_scores(self):
        """Read old feedback scores from a file."""      
        # Check for an existing scores file
        self.old_scores_exist = os.path.isfile(self.scores_file)
        
        # Scores file exists
        if self.old_scores_exist:
        
            # Get the old scores
            with open(self.scores_file, 'r') as f:
                print('Loading old values from: %s\n' %(self.scores_file))                  
                f.readline()  # discard date      
                f.readline()  # discard newline                
                for key in self.old_scores:
                    pattern = key + ':\s+([\d\,]+)'
                    match = re.search(pattern, f.readline()) 
                    if match == None:
                        self.errors.append('old ' + key + 'score not found')
                    else:  
                        self.old_scores[key] = match.group(1)
                        print('old ' + key + ' score : ' + \
                              self.old_scores[key])                
            f.closed        

    def print_header(self):
        """Print the timestamp and username."""
        self.time_stamp  = datetime.today().strftime('%Y-%m-%d %H:%M:%S')
        print('\n' + self.time_stamp + '\n') 
        print('eBay username: ' + self.username + '\n')

        
# -----------------------------------------------------------------------------
# __main__
# -----------------------------------------------------------------------------
if __name__ == "__main__":

    ebay_id, scores_file = get_cmdline_args()

    notifier = Notifier(ebay_id, scores_file)
    