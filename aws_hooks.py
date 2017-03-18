import json

import boto3
from botocore import exceptions
import random


def build_client(f_path='files/aws_creds.json'):
    with open(f_path, 'r') as f:
        d = json.loads(f.read())

    eu_w = 'eu-west-1'
    elasticc = boto3.resource('ec2', 
                 region_name=eu_w,
                 aws_access_key_id=d['access_key_id'],
                 aws_secret_access_key=d['secret_access_key'],
               )
    return elasticc


def launch_node(ec2):
    try:
        r = ec2.create_instances(
              #DryRun=True,
              #DisableApiTermination=True,
              ImageId='ami-405f7226',
              InstanceInitiatedShutdownBehavior='terminate', # NOTE shutdown will destroy the machine
              MinCount=1,
              MaxCount=1,
              KeyName='gl-qual-ass-eu',
              SecurityGroups=['OpenWorld'],
              InstanceType='t2.nano',
              Placement={
                'AvailabilityZone': 'eu-west-1c',
                'Tenancy': 'default',
              },
            )
    except exceptions.ClientError as e:
        print('Instance launch failed with: %s', e)
        return None

    instance = r[0]
    print('Started %s' % instance)
    # Attach tags
    try:
        instance.create_tags(
          Tags=[
            {
              'Key': 'role',
              'Value': 'cielo_test',
            },
            {
              'Key': 'Name',
              'Value': 'gl-16.04-qa-%d' % random.randint(1000,9999),
            },
        ])
    except exceptions.ClientError as e:
        print('Attaching tag failed with: %s', e)
        return None
    
    return r[0]


def terminate_all(ec2, role='cielo_test'):
    instances = ec2.instances.all()
    for instance in instances:
        if instance.tags is None:
            continue
        if has_tag_value(instance, 'role', role):
            try:
                instance.terminate()
                print('Terminated instance: %s' % instance)
            except Exception as e:
                print('Tried to kill %s but saw: %s' % (instance, e))


def has_tag_value(instance, key, value):
    if instance.tags is None:
        return False
    else:
        for dct in instance.tags:
            k, v = dct['Key'], dct['Value']
            if k == key and v == value:
                return True
        return False


def get_newest_instance(ec2):
    ins = [ins for ins in ec2.instances.all() 
            if has_tag_value(ins, 'role', 'cielo_test')]
    ins = sorted(ins, key=lambda x: x.launch_time, reverse=True)
    return ins[0]


if __name__ == '__main__':
    ec2 = build_client()

    #ins = launch_node(ec2)
    #ins = get_newest_instance(ec2)

    terminate_all(ec2)
