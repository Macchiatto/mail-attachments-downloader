""" This script parse and download the attachments of an email """
# coding:utf-8
import os
import poplib
import email
import time
from datetime import datetime
from email._parseaddr import parsedate_tz
import util
from Preprocess import main as predo
import const

__author__ = "Aiden"
__date__ = "2016-12-28"
__copyright__ = "Copyright 2016, wochacha"
__version__ = "1.1.2"


class Email(object):
    """This class is to parse an email and get its attachment files """
    # email configuration
    def __init__(self):
        self.dateDir = datetime.now().strftime("%Y%m%d")
        self.host = const.EMAIL_CONF['host']
        self.port = const.EMAIL_CONF['port']
        self.user_id = const.EMAIL_CONF['user']
        self.pwd = const.EMAIL_CONF['password']
        self.uidl = ''
        self.mail_id = ''
        self.send_date = ''
        self.biz_name = ''
        self.send_datetime = ''


    def main(self):
        """ parse the email and save its attachments """
        mail_server = poplib.POP3(self.host, self.port)
        try:
            mail_server.user(self.user_id)
            mail_server.pass_(self.pwd)
        except poplib.error_proto as e:
            print("Login failed:", e)
            exit(1)
        (mail_count, size) = mail_server.stat()
        print("MailNum: {0}  Size: {1}MB".format(
            mail_count, round(size / 1024 / 1024)))
        results = util.mysql_execute("select uidl from tesla_email")
        # get local uidl list
        loc_uidl = [loc_one[0] for loc_one in results]
        # Get a unique identification of an email
        # construct a list that contains ready-to-download id
        serv_uidl_dic = {serv_one.decode().split(
            )[-1]: serv_one.decode().split()[0] for serv_one in mail_server.uidl()[1]}
        # new email uidl set
        new_uidl = set(serv_uidl_dic.keys()).difference(set(loc_uidl))
        if not new_uidl:
            print("No new emails !")
            exit(0)
        # Loop email sequence
        for uidl in new_uidl:
            self.mail_id = serv_uidl_dic[uidl]
            print('Now downloading the email No.{}'.format(self.mail_id))
            self.parse_email(mail_server, uidl)
            print("=================================")
            # log out from mail server
        mail_server.quit()


    def parse_email(self, mail_conn, uidl):
        """parse email content"""
        messages = mail_conn.retr(self.mail_id)[1]
        content = email.message_from_bytes(
            '\n'.encode('utf-8').join(messages))
        subject = email.header.decode_header(content.get('subject'))
        mail_from = email.utils.parseaddr(content.get("from"))[1]
        print("From:", mail_from)
        raw_date_time = parsedate_tz(content.get('date'))
        # (y, month, d, h, min, sec, _, _, _, tzoffset) = parsedate_tz(content.get('date'))
        # sentDate = "%d-%02d-%02d %02d:%02d:%02d" % (y, month, d, h, min, sec)
        self.send_datetime = time.strftime(
            "%Y-%m-%d %H:%M:%S", raw_date_time[0:-1])
        print("Date:", self.send_datetime)
        self.send_date = time.strftime("%Y%m%d", raw_date_time[:-1])
        sub = self.decode_str(subject[0][0])
        print("Subject:", sub)
        # Insert new email-info into the table: tesla_email
        util.mysql_execute("""INSERT INTO tesla_email(
            uidl, sequence, subject, mail_from, send_date) values(
                '{}', {}, '{}', '{}', '{}') """.format(
                    uidl, self.mail_id, sub, mail_from, self.send_datetime))
        self.download_files(content)


    def download_files(self, mail):
        """download email attachemnts"""
        for part in mail.walk():
            if not part.is_multipart():
                # Start to deal with attachments
                name = part.get_param('name')
                if name:
                    tmp_name = email.header.decode_header(name)
                    filename = self.decode_str(tmp_name[0][0])
                    print('Attachment:', filename)
                    # set download path
                    filepath = os.path.join(const.WIN_EMAIL_DIR, self.send_date)
                    # If not exist, create it
                    if not os.path.exists(filepath):
                        os.makedirs(filepath)
                    filename = self.set_filename(filepath, filename)
                    full_path = os.path.join(filepath, filename)
                    # save file
                    with open(full_path, 'wb') as fo:
                        fo.write(part.get_payload(decode=True))
                    md5 = util.get_file_md5(full_path)
                    file_size = util.format_filesize(full_path)
                    # insert the record into mysql table
                    util.mysql_execute("""INSERT IGNORE INTO importdata.tesla_file(
                        uidl, filename, size, send_date, md5) values (
                            '{}', '{}', '{}', '{}', '{}') """.format(
                                self.mail_id, filename, file_size, self.send_datetime, md5))
                    predo(full_path, 'tesla')
                else:
                    pass
                    # deal with email contents
                    # ch = par.get_content_charset()
                    # if ch == None:
                    #  print(par.get_payload(decode=True).decode())
                    # else:
                    #   print(par.get_payload(decode=True).decode(ch))


    @staticmethod
    def set_filename(filepath, filename, n=1):
        """ dddd"""
        while os.path.exists(os.path.join(filepath, filename)):
            filename = "{}({}).{}".format(
                os.path.splitext(filename)[0], str(n), os.path.splitext(filename)[1])
            n += 1
        return filename


    @staticmethod
    def decode_str(name):
        """if byte string then decode it"""
        if isinstance(name[0][0], bytes):
            try:
                if name[0][1] is None:
                    output_name = name[0][0].decode()
                else:
                    output_name = name[0][0].decode(name[0][1])
            except UnicodeDecodeError:
                output_name = name[0][0].decode('gb18030')
        else:
            output_name = name[0][0]

        return output_name

# main call
if __name__ == '__main__':
    OBJ_GET_EMAIL = Email()
    OBJ_GET_EMAIL.main()

    # mailServer.dele(i)
    # mailServer.quit()
