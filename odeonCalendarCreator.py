# coding=utf8

from __future__ import print_function
from apiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
import pybase64
import email
import pandas as pd
from bs4 import BeautifulSoup
from apiclient import errors
import re
import datetime

# Setup the Gmail API
SCOPES = 'https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/calendar'
store = file.Storage('userCredentialsGoogle.json')
creds = store.get()
if not creds or creds.invalid:
    flow = client.flow_from_clientsecrets('clientSecretGoogle.json', SCOPES)
    creds = tools.run_flow(flow, store)
service = build('gmail', 'v1', http=creds.authorize(Http()))


def listMessagesMatchingQuery(service, user_id, query=''):
    """List all Messages of the user's mailbox matching the query.

    Args:
        service: Authorized Gmail API service instance.
        user_id: User's email address. The special value "me" can be used to indicate the authenticated user.
        query: String used to filter messages returned.
        Eg.- 'from:user@some_domain.com' for Messages from a particular sender.

    Returns:
        List of Messages that match the criteria of the query. Note that the returned list contains Message IDs, you must use get with the appropriate ID to get the details of a Message.
    """
    try:
        response = service.users().messages().list(userId=user_id, q=query).execute()
        if 'messages' in response:
            messages = []
            messages.extend(response['messages'])
        else:
            messages = "false"
        while 'nextPageToken' in response:
            page_token = response['nextPageToken']
            response = service.users().messages().list(userId=user_id, q=query, pageToken=page_token).execute()
            messages.extend(response['messages'])
        return messages
    except errors.HttpError as error:
        print("An error occurred: " + error)


def getMessage(service, user_id, msg_id):
    """`Get a Message with given ID.

    Args:
        service: Authorized Gmail API service instance.
        user_id: User's email address. The special value "me" can be used to indicate the authenticated user.
        msg_id: The ID of the Message required.
    Returns:
        A Message.
    """
    try:
        message = service.users().messages().get(userId=user_id, id=msg_id).execute()

        print('Message snippet: %s' % message['snippet'])
        return message
    except errors.HttpError as error:
        print("An error occurred: " + error)


def getMimeMessage(service, user_id, msg_id):
    """Get a Message and use it to create a MIME Message.

    Args:
        service: Authorized Gmail API service instance.
        user_id: User's email address. The special value "me" can be used to indicate the authenticated user.
        msg_id: The ID of the Message required.
    Returns:
        A MIME Message, consisting of data from Message.
    """
    try:
        message = service.users().messages().get(userId=user_id, id=msg_id, format='raw').execute()
        print('Message snippet: %s' % message['snippet'])
        print("******************************getMimeMessage - message***************************************************")
        print(message)
        print("*********************************************************************************************************")
        msg_str = pybase64.urlsafe_b64decode(message['raw'].encode('ASCII'))
        print("111")
        mime_msg = email.message_from_string(msg_str)
        print("222")
        return mime_msg
    except errors.HttpError as error:
        print("An error occurred:" + error)


def getMessageBody(service, user_id, msg_id):
    try:
        message = service.users().messages().get(userId=user_id, id=msg_id, format='raw').execute()
        msg_str = pybase64.urlsafe_b64decode(message['raw'].encode('ASCII'))
        mime_msg = email.message_from_string(msg_str)
        messageMainType = mime_msg.get_content_maintype()
        if messageMainType == 'multipart':
            for part in mime_msg.get_payload():
                if part.get_content_maintype() == 'text':
                    return part.get_payload()
            return ""
        elif messageMainType == 'text':
            return mime_msg.get_payload()
    except errors.HttpError as error:
        print("An error occurred: %s" % error)


def removeGarbage(message):
    message = re.sub(r"=20", "", message)
    message = re.sub(r"=EF=BF=BD", "£", message)
    message = re.sub(r"=A3", "£", message)
    message = re.sub(r"\.[\s]*[\n]+", "\n", message)
    return message


def getLocation(message):
    # location = message.partition('Cinema:-')
    # regex = r"^([\s\S]*Cinema:\s)"
    # regex = r"^([\s\S]*Cinema)"
    # regex = r"^[\s\S]*Cinema "
    regex = r"^([\s\S]*Cinema:\s)"
    location = re.sub(regex, "", message)
    regex2 = r"\n[\s\S]*"
    location = re.sub(regex2, "", location)
    # location = location.splitlines()

    # search = re.search(r"^Cinema:\s([.*\n]+)", message, re.IGNORECASE)

    # if search:
    #     location = search.group(1)

    # matches = re.finditer(r"^Cinema:\s([^\n]+)", message, re.MULTILINE)
    # location = matches[1]
    return location


# def getHtmlFromMessage(message):
#     html = re.sub('^(.*)(?=\<html)', "", str(message))
#     html = re.match("<html(.*?)",str(message)).group()
#     return "<html" + html


def getFilm(message):
    regex = r"^([\s\S]*To see:\s)"
    film = re.sub(regex, "", message)
    regex2 = r"\n[\s\S]*"
    film = re.sub(regex2, "", film)

    return film


def getDate(message):
    regex = r"^([\s\S]*On:\s)"
    date = re.sub(regex, "", message)
    regex2 = r"\n[\s\S]*"
    date = re.sub(regex2, "", date)

    return date


def getScreen(message):
    regex = r"^([\s\S]*Auditorium:[\s]*\n)"
    screen = re.sub(regex, "", message)
    regex2 = r"\n[\s\S]*"
    screen = re.sub(regex2, "", screen)

    return screen


def getSection(message):
    regex = r"^([\s\S]*Section:\s)"
    section = re.sub(regex, "", message)
    regex2 = r"\n[\s\S]*"
    section = re.sub(regex2, "", section)

    return section


def getSeats(message):
    regex = r"^([\s\S]*Seats:[\s]*\n)"
    seats = re.sub(regex, "", message)
    regex2 = r"\n[\s\S]*"
    seats = re.sub(regex2, "", seats)

    return seats


def getTickets(message):
    regex = r"^([\s\S]*Tickets\*:[\s]*\n)"
    tickets = re.sub(regex, "", message)
    regex2 = r"\n[\s\S]*"
    tickets = re.sub(regex2, "", tickets)

    return tickets


def getBookingRef(message):
    regex = r"^([\s\S]*Your booking reference is:\s)"
    bookingRef = re.sub(regex, "", message)
    regex2 = r"\n[\s\S]*"
    bookingRef = re.sub(regex2, "", bookingRef)

    # add check to see if last char is a dot, if so remove it

    return bookingRef


def scrapeOdeonTable(message):
    soup = BeautifulSoup(message, 'lxml')  # Parse the HTML as a string

    table = soup.find_all('table')[0]  # Grab the first table

    new_table = pd.DataFrame(columns=range(0, 2), index=[0])  # I know the size

    row_marker = 0
    for row in table.find_all('tr'):
        column_marker = 0
        columns = row.find_all('td')
        for column in columns:
            new_table.iat[row_marker, column_marker] = column.get_text()
            column_marker += 1

    return new_table


messages = listMessagesMatchingQuery(service, 'me', 'from:(booking@odeoncinemas.info) subject:(ODEON BOOKING CONFIRMATION)')


if messages == "false":
    print("No Messages match that query, or there was a problem")
else:
    for message in messages:
        fullMessage = getMessageBody(gmailService, 'me', message['id'])
        fullMessage = removeGarbage(fullMessage)

        print("***************** NEW MSG ***********************")
        # print("************************* MSG BEGINS *************************************")
        # print(fullMessage)
        # print("************************* MSG   ENDS *************************************")

        print("Location:" + getLocation(fullMessage))

        print("Film:" + getFilm(fullMessage))

        print("Date:" + getDate(fullMessage))

        print("Screen:" + getScreen(fullMessage))

        # print("Section:" + getSection(fullMessage)) #Standard/Premium

        print("Seat:" + getSeats(fullMessage))  # Likely multiple

        print("Tickets:" + getTickets(fullMessage))

        print("Booking Ref:" + getBookingRef(fullMessage))


gcalService = build('calendar', 'v3', http=creds.authorize(Http()))

# Call the Calendar API
now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
print('Getting the upcoming 10 events')
events_result = gcalService.events().list(calendarId='primary', timeMin=now, maxResults=10, singleEvents=True, orderBy='startTime').execute()
events = events_result.get('items', [])

if not events:
    print('No upcoming events found.')
for event in events:
    start = event['start'].get('dateTime', event['start'].get('date'))
    print(start, event['summary'])
