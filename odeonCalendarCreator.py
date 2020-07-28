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
from datetime import datetime
import json
import pytz

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
        msg_str = pybase64.urlsafe_b64decode(message['raw'].encode('UTF-8'))
        mime_msg = email.message_from_string(msg_str.decode())
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
    shortMessage = re.findall(r"(Cinema:[\s\S]*?Your booking reference is:\s+[\d]*)", message)
    try:
        shortMessage = re.sub(r"(<[\S]*?>|[ ]*=20)", "", shortMessage[0])
    except IndexError:
        print("failed message main body")
        print(json.dumps(message))
        return False


def getLocation(message):
    # location = message.partition('Cinema:-')
    # regex = r"^([\s\S]*Cinema:\s)"
    # regex = r"^([\s\S]*Cinema)"
    # regex = r"^[\s\S]*Cinema "
    # regex = r"^([\s\S]*Cinema:\s)"
    # location = re.sub(regex, "", message)
    # regex2 = r"\n[\s\S]*"
    # location = re.sub(regex2, "", location)
    # location = location.splitlines()

    # search = re.search(r"^Cinema:\s([.*\n]+)", message, re.IGNORECASE)

    # if search:
    #     location = search.group(1)

    # matches = re.finditer(r"^Cinema:\s([^\n]+)", message, re.MULTILINE)
    # location = matches[1]
    regex = r"Cinema:\s+([\S\s]*?)[\r\n]+"
    matches = re.findall(regex, message)
    try:
        location = matches[0]
    except IndexError:
        location = False

    return location


# def getHtmlFromMessage(message):
#     html = re.sub('^(.*)(?=\<html)', "", str(message))
#     html = re.match("<html(.*?)",str(message)).group()
#     return "<html" + html


def getFilm(message):
    regex = r"To see:\s([\S\s]*?)[\r\n]+"
    matches = re.findall(regex, message)
    try:
        film = matches[0]
    except IndexError:
        film = False

    return film


def getDate(message):
    regex = r"[\r\n]On: ([\S\s]*?)[\r\n]"
    matches = re.findall(regex, message)
    try:
        date = matches[0]
    except IndexError:
        date = False

    dateTimeObj = datetime.strptime(date, "%d/%m/%Y %H:%M %p")

    ukTime = pytz.timezone("Europe/London")
    ukDateTimeObj = ukTime.localize(dateTimeObj)

    return ukDateTimeObj


def getScreen(message):
    regex = r"Auditorium:[\s]*Screen[\s]*([\s\S]*?)[\n\r]"
    matches = re.findall(regex, message)
    try:
        screen = matches[0]
    except IndexError:
        return False

    screen = int(screen)

    return screen


def getSection(message):
    regex = r"^([\s\S]*Section:\s)"
    section = re.sub(regex, "", message)
    regex2 = r"\n[\s\S]*"
    section = re.sub(regex2, "", section)

    return section


def getSeats(message):
    # Only captures first line of seats - needs to capture as many lines as there are
    regex = r"Seats:[\s]*([\s\S]*?)[\n\r]+Tickets"
    seatsStr = re.findall(regex, message)
    regex2 = r"Row[\s]([\s\S]*?)[\s]Seat[\s]([\d]+)"
    try:
        seats = re.findall(regex2, seatsStr[0])
    except IndexError:
        return False

    seatsNew = []
    for seat in seats:
        seatNew = [seat[0], int(seat[1])]
        seatsNew.append(seatNew)

    return seatsNew


def getTickets(message):
    # Only captures first line of tickets - needs to capture as many lines as there are
    regex = r"Tickets[\s\S]*?[\n\r]{2}([\s\S]*?)[\n\r]{4}"
    ticketsStr = re.findall(regex, message)
    regex2 = r"[\n\r]*([\s\S]+?): £([\d]+?.[\d]+)"
    tickets = re.findall(regex2, ticketsStr[0])
    ticketsNew = []
    for ticket in tickets:
        ticketNew = [ticket[0], float(ticket[1])]
        ticketsNew.append(ticketNew)

    return ticketsNew


def getBookingRef(message):
    regex = r"Your booking reference is:[\s]+([\d]*)"
    matches = re.findall(regex, message)
    try:
        bookingRef = matches[0]
    except IndexError:
        bookingRef = False

    return bookingRef


def getTotalCost(message):
    regex = r"The amount of £([\d.]*?)[\s]"
    matches = re.findall(regex, message)
    try:
        totalCost = float(matches[0])
    except IndexError:
        totalCost = False

    return totalCost


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

messageSuccessCount = 0
locationSuccessCount = 0
filmSuccessCount = 0
dateSuccessCount = 0
screenSuccessCount = 0
seatsSuccessCount = 0
ticketsSuccessCount = 0
bookingRefSuccessCount = 0
totalCostSuccessCount = 0

try:
    with open("data.json") as json_file:
        data = json.load(json_file)
        if data["messagesProcessedOk"]:
            messagesProcessedOk = data["messagesProcessedOk"]
        else:
            messagesProcessedOk = []
except Exception:
    messagesProcessedOk = []

if messages == "false":
    print("No Messages match that query, or there was a problem")
    exit(0)
else:
    for message in messages:
        if message['id'] in messagesProcessedOk:
            # This message has been processed already, skip it
            continue

        # Reset processed OK variable
        messageProcessedOk = False
        fullMessage = getMessageBody(service, 'me', message['id'])
        # print(json.dumps(fullMessage))
        # fullMessage = fullMessage.decode("utf-8")
        if not fullMessage:
            # There is no message body here, very wierd, let's move on though
            continue
        fullMessage = removeGarbage(fullMessage)

        messageSuccessCount += 1

        print("***************** NEW MSG ***********************")
        print("************************* MSG BEGINS *************************************")
        print(fullMessage)
        print("************************* MSG   ENDS *************************************")

        location = getLocation(fullMessage)
        if location:
            locationSuccessCount += 1
        print("Location:" + json.dumps(location))
        del location

        film = getFilm(fullMessage)
        if film:
            filmSuccessCount += 1
        print("Film:" + json.dumps(film))
        del film

        date = getDate(fullMessage)
        if date:
            dateSuccessCount += 1
            strDate = str(date)
        print("Date:" + strDate + " Zone: " + str(date.tzinfo))
        del date

        screen = getScreen(fullMessage)
        if screen:
            screenSuccessCount += 1
        print("Screen:" + json.dumps(screen))
        del screen

        # print("Section:" + json.dumps(getSection(fullMessage))) # Standard/Premium

        seats = getSeats(fullMessage)
        if seats:
            seatsSuccessCount += 1
        print("Seat:" + json.dumps(seats))  # Likely multiple
        del seats

        tickets = getTickets(fullMessage)
        if tickets:
            ticketsSuccessCount += 1
        print("Tickets:" + json.dumps(tickets))  # Likely multiple
        del tickets

        bookingRef = getBookingRef(fullMessage)
        if bookingRef:
            bookingRefSuccessCount += 1
        print("Booking Ref:" + json.dumps(bookingRef))
        del bookingRef

        totalCost = getTotalCost(fullMessage)
        if totalCost:
            totalCostSuccessCount += 1
        print("Total Cost:" + json.dumps(totalCost))
        del totalCost

        # For the time being let's assume it was Processed OK
        messageProcessedOk = True

        if messageProcessedOk is True:
            # Do Something
            messagesProcessedOk.append(message['id'])

data = {"messagesProcessedOk": messagesProcessedOk}

with open('data.json', 'w') as outfile:
    json.dump(data, outfile)

print("Got " + str(messageSuccessCount) + " of " + str(len(messages)) + " messages OK")
print("Location: " + str(locationSuccessCount))
print("Film: " + str(filmSuccessCount))
print("Date: " + str(dateSuccessCount))
print("Screen: " + str(screenSuccessCount))
print("Seats: " + str(seatsSuccessCount))
print("Tickets: " + str(ticketsSuccessCount))
print("Booking Ref: " + str(bookingRefSuccessCount))
print("Total Cost: " + str(totalCostSuccessCount))

exit(0)
gcalService = build('calendar', 'v3', http=creds.authorize(Http()))

# Call the Calendar API
now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
print('Getting the upcoming 10 events')
events_result = gcalService.events().list(calendarId='primary', timeMin=now, maxResults=10, singleEvents=True, orderBy='startTime').execute()
events = events_result.get('items', [])

if not events:
    print('No upcoming events found.')
for event in events:
    start = event['start'].get('dateTime', event['start'].get('date'))
    print(start, event['summary'])
